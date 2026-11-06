// Copyright 2026 The Helium Authors
// You can use, redistribute, and/or modify this source code under
// the terms of the GPL-3.0 license that can be found in the LICENSE file.
import AppKit
import SwiftUI

// Preserve explicit schemes while allowing the usual host-only prefix editing.
func arcCompletionText(_ completion: String, query: String) -> String {
    let folded = query.lowercased()
    if completion.lowercased().hasPrefix(folded) { return completion }
    for scheme in ["https://", "http://"] where completion.lowercased().hasPrefix(scheme) {
        let hostText = String(completion.dropFirst(scheme.count))
        if hostText.lowercased().hasPrefix(folded) { return hostText }
    }
    return completion
}

private final class CommandState: ObservableObject {
    @Published var rows: [[String: Any]] = []
    @Published var selected = 0
    @Published var destination = "Search"
    @Published var surface = NSColor.windowBackgroundColor
    @Published var accent = NSColor.controlAccentColor
    @Published var onAccent = NSColor.white
    @Published var foreground = NSColor.labelColor
    @Published var secondary = NSColor.secondaryLabelColor
    var rawQuery = ""
    var movedSelection = false
    weak var field: NSTextField?
    var event: (Int, String, Int) -> Void
    init(event: @escaping (Int, String, Int) -> Void) { self.event = event }
    func move(_ direction: Int) {
        guard !rows.isEmpty else { return }
        selected = (selected + direction + rows.count) % rows.count
        movedSelection = true
        let text = arcCompletionText(rows[selected]["input"] as? String ?? rawQuery, query: rawQuery)
        field?.stringValue = text
        if let editor = field?.currentEditor() {
            editor.string = text
            editor.selectedRange = NSRange(location: (text as NSString).length, length: 0)
        }
        event(4, "", selected)
    }
}

private final class CommandQueryField: NSTextField {
    var search: (() -> Void)?
    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        if event.keyCode == 36 && event.modifierFlags.contains(.command) {
            if let editor = currentEditor() as? NSTextView, editor.hasMarkedText() { return false }
            search?()
            return true
        }
        return super.performKeyEquivalent(with: event)
    }
}
private struct QueryInput: NSViewRepresentable {
    @ObservedObject var state: CommandState
    func makeCoordinator() -> Coordinator { Coordinator(state) }
    func makeNSView(context: Context) -> NSTextField {
        let field = CommandQueryField()
        field.search = { [weak state] in state?.event(3, state?.rawQuery ?? "", state?.selected ?? 0) }
        field.isBordered = false
        field.drawsBackground = false
        field.focusRingType = .none
        field.font = .systemFont(ofSize: 18, weight: .medium)
        field.placeholderString = "Search or Enter URL…"
        field.delegate = context.coordinator
        field.setAccessibilityLabel("Search, enter a URL, or ask ChatGPT")
        field.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        state.field = field
        return field
    }
    func updateNSView(_ field: NSTextField, context: Context) {
        field.textColor = state.foreground
        field.placeholderAttributedString = NSAttributedString(
            string: "Search or Enter URL…",
            attributes: [.foregroundColor: state.foreground.withAlphaComponent(0.55),
                         .font: NSFont.systemFont(ofSize: 18, weight: .medium)])
    }
    final class Coordinator: NSObject, NSTextFieldDelegate {
        let state: CommandState
        init(_ state: CommandState) { self.state = state }
        func controlTextDidChange(_ notification: Notification) {
            guard let field = notification.object as? NSTextField else { return }
            if let editor = field.currentEditor() as? NSTextView, editor.hasMarkedText() { return }
            state.rawQuery = field.stringValue
            state.movedSelection = false
            state.event(1, field.stringValue, 0)
        }
        func control(_ control: NSControl, textView: NSTextView, doCommandBy selector: Selector) -> Bool {
            if textView.hasMarkedText() { return false }
            switch selector {
            case #selector(NSResponder.moveDown(_:)): state.move(1)
            case #selector(NSResponder.moveUp(_:)): state.move(-1)
            case #selector(NSResponder.insertNewline(_:)):
                let search = NSApp.currentEvent?.modifierFlags.contains(.command) == true
                state.event(search ? 3 : 2, state.rawQuery, state.selected)
            case #selector(NSResponder.cancelOperation(_:)): state.event(5, "", 0)
            default: return false
            }
            return true
        }
    }
}

private struct CommandSurface: View {
    @ObservedObject var state: CommandState
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    var body: some View {
        VStack(spacing: 4) {
            HStack(spacing: 12) {
                Image(systemName: state.rows.indices.contains(state.selected) ? state.rows[state.selected]["symbol"] as? String ?? "magnifyingglass" : "magnifyingglass")
                    .font(.system(size: 17)).frame(width: 20)
                QueryInput(state: state)
            }
            .padding(.horizontal, 16).frame(height: 56)
            Divider().opacity(0.3)
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 4) {
                        ForEach(state.rows.indices, id: \.self) { index in
                            let row = state.rows[index]
                            let selected = index == state.selected
                            Button { state.event(7, state.rawQuery, index) } label: {
                                HStack(spacing: 12) {
                                    Group {
                                        if let icon = row["favicon"] as? NSImage {
                                            Image(nsImage: icon).resizable().scaledToFit()
                                        } else {
                                            Image(systemName: row["symbol"] as? String ?? "globe")
                                        }
                                    }.frame(width: 20, height: 20)
                                    HStack(spacing: 4) {
                                        Text(row["title"] as? String ?? "")
                                            .font(.system(size: 13, weight: .medium)).layoutPriority(1)
                                        if row["action"] as? String == "Open", let detail = row["detail"] as? String, !detail.isEmpty {
                                            Text("— " + detail).font(.system(size: 13)).opacity(0.45)
                                        }
                                    }.lineLimit(1).frame(maxWidth: .infinity, alignment: .leading)
                                    let action = row["action"] as? String ?? ""
                                    if action != "Open" && !action.isEmpty {
                                        Text(action).font(.system(size: 12, weight: .medium))
                                            .opacity(selected ? 1 : 0.4)
                                    }
                                    if action == "Switch to Tab" {
                                        Image(systemName: "arrow.right").font(.system(size: 16, weight: .medium))
                                            .frame(width: 24, height: 24)
                                            .foregroundColor(selected ? Color(nsColor: state.accent) : Color(nsColor: state.foreground).opacity(0.45))
                                            .background(selected ? Color(nsColor: state.onAccent) : Color(nsColor: state.foreground).opacity(0.05), in: RoundedRectangle(cornerRadius: 5))
                                    } else if action.contains("⌘") {
                                        EmptyView()
                                    }
                                }
                                .padding(.horizontal, 10).frame(height: 46)
                                .foregroundColor(Color(nsColor: selected ? state.onAccent : state.foreground))
                                .background(selected ? Color(nsColor: state.accent).opacity(0.88) : .clear, in: RoundedRectangle(cornerRadius: 7))
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain).id(index)
                            .accessibilityLabel("\(row["title"] as? String ?? "") \(row["action"] as? String ?? "")")
                            .accessibilityHint("Enter to open. Command Enter searches your original text.")
                            .accessibilityAddTraits(selected ? .isSelected : [])
                        }
                    }
                }
                .onChange(of: state.selected) { value in
                    if reduceMotion { proxy.scrollTo(value) }
                    else { withAnimation(.easeOut(duration: 0.12)) { proxy.scrollTo(value) } }
                }
            }
        }
        .padding(10)
        .foregroundColor(Color(nsColor: state.foreground))
        .background(Color(nsColor: state.surface).opacity(reduceTransparency ? 1 : 0.38))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(Color.white.opacity(0.14), lineWidth: 0.5))
    }
}
private final class ClearHostingView<Content: View>: NSHostingView<Content> {
    override var isOpaque: Bool { false }
}

@objc(HeliumCommandBarHost) public final class HeliumCommandBarHost: NSObject {
    private let state: CommandState
    @objc public let view: NSView
    @objc(initWithEvent:) public init(event: @escaping (Int, String, Int) -> Void) {
        let model = CommandState(event: event)
        state = model
        let effect = NSVisualEffectView()
        effect.material = .popover
        effect.blendingMode = .behindWindow
        effect.state = .active
        effect.wantsLayer = true
        effect.layer?.cornerRadius = 12
        effect.layer?.masksToBounds = true
        let content = ClearHostingView(rootView: CommandSurface(state: model))
        content.translatesAutoresizingMaskIntoConstraints = false
        effect.addSubview(content)
        NSLayoutConstraint.activate([
            content.leadingAnchor.constraint(equalTo: effect.leadingAnchor),
            content.trailingAnchor.constraint(equalTo: effect.trailingAnchor),
            content.topAnchor.constraint(equalTo: effect.topAnchor),
            content.bottomAnchor.constraint(equalTo: effect.bottomAnchor)])
        view = effect
        super.init()
    }
    @objc public func invalidate() { state.event = { _, _, _ in } }
    @objc public func setText(_ text: String) {
        state.field?.stringValue = text
        state.rawQuery = text
        state.movedSelection = false
        state.event(1, text, 0)
    }
    @objc public func focus() {
        view.layoutSubtreeIfNeeded()
        guard let field = state.field else { return }
        field.window?.makeFirstResponder(field)
    }
    @objc(updateWithRows:selected:destination:colors:)
    public func update(rows: [[String: Any]], selected: Int, destination: String, colors: [NSColor]) {
        state.rows = rows
        state.selected = selected
        state.destination = destination
        if !state.movedSelection, let field = state.field,
           let editor = field.currentEditor() as? NSTextView, !editor.hasMarkedText() {
            var presentation = state.rawQuery
            var selection = NSRange(location: state.rawQuery.utf16.count, length: 0)
            if !state.rawQuery.isEmpty, let first = rows.first,
               let input = first["input"] as? String,
               case let completion = arcCompletionText(input, query: state.rawQuery),
               (first["action"] as? String == "Switch to Tab" || first["action"] as? String == "Open"),
               completion.lowercased().hasPrefix(state.rawQuery.lowercased()),
               completion.utf16.count > state.rawQuery.utf16.count {
                presentation = completion
                selection.length = completion.utf16.count - state.rawQuery.utf16.count
            }
            // An asynchronous result change can remove the completion. Restore
            // the raw query then, rather than leaving a stale URL in the field.
            if field.stringValue != presentation {
                field.stringValue = presentation
                editor.string = presentation
                editor.selectedRange = selection
            }
        }
        if colors.count == 5 {
            state.surface = colors[0]; state.accent = colors[1]; state.onAccent = colors[2]
            state.foreground = colors[3]; state.secondary = colors[4]
        }
    }
}

private final class AppearanceState: ObservableObject {
    @Published var colors: [Color]
    @Published var intensity: Double
    @Published var suggestions: Bool
    @Published var grain: Bool
    @Published var scheme: Int
    @Published var density: Int
    @Published var tile: Int
    let event: (String, String) -> Void
    init(values: [String: String], event: @escaping (String, String) -> Void) {
        self.event = event
        let parsed: [Color] = (values["colors"] ?? "#7aa89c").split(separator: ",").compactMap {
            let hex = String($0).replacingOccurrences(of: "#", with: "")
            guard let n = UInt32(hex, radix: 16) else { return nil }
            return Color(red: Double(n >> 16 & 255) / 255, green: Double(n >> 8 & 255) / 255, blue: Double(n & 255) / 255)
        }
        colors = parsed.isEmpty ? [Color(red: 0.48, green: 0.66, blue: 0.61)] : parsed
        intensity = Double(values["intensity"] ?? "50") ?? 50
        grain = values["grain"] == "true"
        suggestions = values["suggestions"] != "false"
        scheme = Int(values["scheme"] ?? "0") ?? 0
        density = Int(values["density"] ?? "1") ?? 1
        tile = Int(values["tile"] ?? "48") ?? 48
    }
    func saveColors() {
        let text = colors.map { color -> String in
            let c = NSColor(color).usingColorSpace(.sRGB) ?? .gray
            return String(format: "#%02x%02x%02x", Int((c.redComponent * 255).rounded()), Int((c.greenComponent * 255).rounded()), Int((c.blueComponent * 255).rounded()))
        }.joined(separator: ",")
        event("colors", text)
    }
}
private struct AppearanceSurface: View {
    @ObservedObject var state: AppearanceState
    private let presets: [[Color]] = [
        [Color(red: 0.48, green: 0.66, blue: 0.61), Color(red: 0.78, green: 0.88, blue: 0.79)],
        [Color(red: 0.94, green: 0.56, blue: 0.43), Color(red: 0.98, green: 0.77, blue: 0.61)],
        [Color(red: 0.49, green: 0.56, blue: 0.79), Color(red: 0.74, green: 0.65, blue: 0.85)],
        [Color(red: 0.33, green: 0.37, blue: 0.42)]]
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Make it yours").font(.system(size: 22, weight: .semibold))
            RoundedRectangle(cornerRadius: 14)
                .fill(LinearGradient(colors: state.colors, startPoint: .topLeading, endPoint: .bottomTrailing))
                .overlay(RoundedRectangle(cornerRadius: 8).fill(.background).padding(12).padding(.leading, 76))
                .frame(height: 110).accessibilityLabel("Browser theme preview")
            Picker("Appearance", selection: $state.scheme) {
                Text("System").tag(0); Text("Light").tag(1); Text("Dark").tag(2)
            }.pickerStyle(.segmented).onChange(of: state.scheme) { state.event("scheme", String($0)) }
            HStack(spacing: 12) {
                ForEach(presets.indices, id: \.self) { i in
                    Button { state.colors = presets[i]; state.saveColors() } label: {
                        Circle().fill(LinearGradient(colors: presets[i], startPoint: .topLeading, endPoint: .bottomTrailing)).frame(width: 30, height: 30)
                    }.buttonStyle(.plain).accessibilityLabel(["Mint", "Coral", "Lavender", "Graphite"][i])
                }
                Spacer()
                Button { if state.colors.count < 3 { state.colors.append(state.colors.last ?? .gray); state.saveColors() } } label: { Image(systemName: "plus") }
                    .disabled(state.colors.count == 3).help("Add gradient color")
                Button { if state.colors.count > 1 { state.colors.removeLast(); state.saveColors() } } label: { Image(systemName: "minus") }
                    .disabled(state.colors.count == 1).help("Remove gradient color")
            }
            HStack {
                ForEach(state.colors.indices, id: \.self) { i in
                    ColorPicker("Color \(i + 1)", selection: $state.colors[i], supportsOpacity: false)
                }
            }.onChange(of: state.colors) { _ in state.saveColors() }
            VStack(alignment: .leading) {
                Text("Color intensity")
                Slider(value: $state.intensity, in: 10...100, step: 1)
                    .onChange(of: state.intensity) { state.event("intensity", String(Int($0))) }
            }
            Toggle("Subtle grain", isOn: $state.grain).onChange(of: state.grain) { state.event("grain", String($0)) }
            Divider()
            Picker("Spacing", selection: $state.density) {
                Text("Compact").tag(0); Text("Comfortable").tag(1)
            }.onChange(of: state.density) { state.event("density", String($0)) }
            Picker("Pinned tiles", selection: $state.tile) {
                ForEach([40, 48, 56, 64, 72], id: \.self) { Text("\($0) pt").tag($0) }
            }.onChange(of: state.tile) { state.event("tile", String($0)) }
            Toggle("Online search suggestions", isOn: $state.suggestions)
                .help("Send typed queries to your default search engine. Private windows stay local.")
                .onChange(of: state.suggestions) { state.event("suggestions", String($0)) }
            HStack {
                Button("Reset appearance") { state.event("reset", ""); state.event("close", "") }
                Spacer()
                Button("Done") { state.event("close", "") }.keyboardShortcut(.defaultAction)
            }
        }.padding(24).frame(width: 360).background(.regularMaterial)
    }
}
@objc(HeliumAppearanceHost) public final class HeliumAppearanceHost: NSObject {
    @objc public let view: NSView
    @objc(initWithValues:event:) public init(values: [String: String], event: @escaping (String, String) -> Void) {
        view = NSHostingView(rootView: AppearanceSurface(state: AppearanceState(values: values, event: event)))
        super.init()
    }
}
