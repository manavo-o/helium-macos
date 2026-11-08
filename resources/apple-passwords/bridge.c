#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <pthread.h>
#include <fcntl.h>
#include <time.h>

#define SOCKET_PATH "/tmp/xenon_passwords.sock"

static int sock_fd = -1;

void log_msg(const char *msg) {
    FILE *f = fopen("/tmp/xenon_bridge_c.log", "a");
    if (f) {
        time_t now = time(NULL);
        char buf[64];
        ctime_r(&now, buf);
        buf[strlen(buf)-1] = '\0';
        fprintf(f, "[%s] %s\n", buf, msg);
        fclose(f);
    }
}

int try_connect(void) {
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) return -1;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) == 0) {
        return fd;
    }
    close(fd);
    return -1;
}

void ensure_daemon(void) {
    sock_fd = try_connect();
    if (sock_fd >= 0) return;

    log_msg("Daemon not connected, attempting to launch daemon...");

    // Find node binary across common paths
    const char *node_paths[] = {
        "/opt/homebrew/bin/node",
        "/usr/local/bin/node",
        "/usr/bin/node"
    };
    const char *node_bin = NULL;
    for (int i = 0; i < 3; i++) {
        if (access(node_paths[i], X_OK) == 0) {
            node_bin = node_paths[i];
            break;
        }
    }

    if (!node_bin) {
        log_msg("Error: could not find node binary");
        return;
    }

    char daemon_script[512];
    const char *home = getenv("HOME");
    if (!home) home = "/Users/manavarunanthi";
    snprintf(daemon_script, sizeof(daemon_script), "%s/.local/share/xenon/apple-passwords/daemon.js", home);

    pid_t pid = fork();
    if (pid == 0) {
        // Child
        int devnull = open("/dev/null", O_RDWR);
        if (devnull >= 0) {
            dup2(devnull, 0);
            dup2(devnull, 1);
            dup2(devnull, 2);
            close(devnull);
        }
        execl(node_bin, "node", daemon_script, (char *)NULL);
        _exit(1);
    }

    // Wait up to 5 seconds for socket
    for (int i = 0; i < 25; i++) {
        usleep(200000); // 200ms
        sock_fd = try_connect();
        if (sock_fd >= 0) {
            log_msg("Successfully connected to newly launched daemon");
            return;
        }
    }
    log_msg("Failed to connect to daemon after waiting");
}

void *socket_to_stdout_thread(void *arg) {
    char buf[16384];
    while (1) {
        ssize_t n = read(sock_fd, buf, sizeof(buf));
        if (n <= 0) break;
        ssize_t written = 0;
        while (written < n) {
            ssize_t w = write(STDOUT_FILENO, buf + written, n - written);
            if (w <= 0) break;
            written += w;
        }
    }
    _exit(0);
    return NULL;
}

int main(int argc, char *argv[]) {
    log_msg("Bridge process started by Xenon");

    ensure_daemon();
    if (sock_fd < 0) {
        log_msg("Fatal: sock_fd is invalid, exiting");
        return 1;
    }

    log_msg("Bridge connected, starting I/O forwarding");

    pthread_t tid;
    pthread_create(&tid, NULL, socket_to_stdout_thread, NULL);

    // Stdin to socket
    char buf[16384];
    while (1) {
        ssize_t n = read(STDIN_FILENO, buf, sizeof(buf));
        if (n <= 0) break;
        ssize_t written = 0;
        while (written < n) {
            ssize_t w = write(sock_fd, buf + written, n - written);
            if (w <= 0) break;
            written += w;
        }
    }

    log_msg("Stdin closed, bridge exiting");
    close(sock_fd);
    return 0;
}
