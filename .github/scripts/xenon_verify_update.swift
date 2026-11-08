import CryptoKit
import Foundation

let arguments = CommandLine.arguments
guard arguments.count == 4,
      let publicKey = Data(base64Encoded: arguments[2]),
      let signature = Data(base64Encoded: arguments[3]) else {
    fatalError("Expected an archive, its embedded public key, and the signature")
}
let key = try Curve25519.Signing.PublicKey(rawRepresentation: publicKey)
let archive = try Data(contentsOf: URL(fileURLWithPath: arguments[1]), options: .mappedIfSafe)
guard key.isValidSignature(signature, for: archive) else {
    fatalError("The update signature does not match the key embedded in Xenon")
}
