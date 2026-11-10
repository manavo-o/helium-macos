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
    var pointerLocation = NSEvent.mouseLocation
    weak var field: NSTextField?
    var event: (Int, String, Int) -> Void
    init(event: @escaping (Int, String, Int) -> Void) { self.event = event }
    func hover(_ index: Int) {
        let location = NSEvent.mouseLocation
        guard location != pointerLocation, rows.indices.contains(index) else { return }
        pointerLocation = location
        selected = index
        event(4, "", index)
    }
    func move(_ direction: Int) {
        guard !rows.isEmpty else { return }
        selected = (selected + direction + rows.count) % rows.count
        movedSelection = true
        pointerLocation = NSEvent.mouseLocation
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

private func matchedText(_ text: String, query: String) -> AttributedString {
    var value = AttributedString(text)
    for token in query.split(whereSeparator: { $0.isWhitespace }) {
        if let range = value.range(of: String(token), options: [.caseInsensitive, .diacriticInsensitive]) {
            value[range].font = .system(size: 13, weight: .bold)
        }
    }
    return value
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
                                        Text(matchedText(row["title"] as? String ?? "", query: state.rawQuery))
                                            .font(.system(size: 13, weight: .medium)).layoutPriority(1)
                                        if row["action"] as? String == "Open", let detail = row["detail"] as? String, !detail.isEmpty {
                                            Text(matchedText("— " + detail, query: state.rawQuery)).font(.system(size: 13)).opacity(0.45)
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
                            .onContinuousHover { phase in
                                if case .active = phase { state.hover(index) }
                            }
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
        if let editor = state.field?.currentEditor() {
            editor.string = text
            editor.selectedRange = NSRange(location: 0, length: text.utf16.count)
        }
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

private struct MaterialPreview: NSViewRepresentable {
    var colors: [Color]
    var intensity: Double
    var grain: Bool
    var scheme: Int
    func makeNSView(context: Context) -> MaterialPreviewView { MaterialPreviewView() }
    func updateNSView(_ view: MaterialPreviewView, context: Context) {
        view.colors = colors.map { NSColor($0) }
        view.intensity = intensity; view.grain = grain
        view.appearance = scheme == 0 ? nil : NSAppearance(named: scheme == 2 ? .darkAqua : .aqua)
        view.needsDisplay = true
    }
}
private final class MaterialPreviewView: NSView {
    var colors: [NSColor] = []
    var intensity = 50.0
    var grain = false
    override var isFlipped: Bool { true }
    private static let noise: NSImage = {
        let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 128, pixelsHigh: 128,
            bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
            colorSpaceName: .deviceRGB, bytesPerRow: 512, bitsPerPixel: 32)!
        for y in 0..<128 { for x in 0..<128 {
            var hash = UInt32(x + y * 128 + 1)
            hash = (hash ^ (hash >> 16)) &* 0x7feb352d
            hash = (hash ^ (hash >> 15)) &* 0x846ca68b
            hash ^= hash >> 16
            let tone: CGFloat = hash & 1 == 1 ? 1 : 0
            rep.setColor(NSColor(srgbRed: tone, green: tone, blue: tone,
                alpha: CGFloat((hash >> 8) % 15) / 255), atX: x, y: y)
        } }
        let image = NSImage(size: NSSize(width: 64, height: 64))
        image.addRepresentation(rep)
        return image
    }()
    override func draw(_ dirtyRect: NSRect) {
        NSGraphicsContext.saveGraphicsState()
        NSBezierPath(roundedRect: bounds, xRadius: 14, yRadius: 14).addClip()
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        let surface = NSColor.windowBackgroundColor.usingColorSpace(.sRGB) ?? .gray
        let weight = floor(min(100, max(10, intensity)) * (dark ? 1.1 : 1.9)) / 255
        let mixed = colors.map { color -> NSColor in
            let c = color.usingColorSpace(.sRGB) ?? .gray
            return NSColor(srgbRed: c.redComponent * weight + surface.redComponent * (1-weight),
                green: c.greenComponent * weight + surface.greenComponent * (1-weight),
                blue: c.blueComponent * weight + surface.blueComponent * (1-weight), alpha: 1)
        }
        if let first = mixed.first {
            first.setFill(); bounds.fill()
            if mixed.count > 1 {
                NSGradient(colors: mixed)?.draw(from: bounds.origin,
                    to: NSPoint(x: bounds.maxX, y: bounds.maxY), options: [.drawsBeforeStartingLocation, .drawsAfterEndingLocation])
            }
        }
        if grain { NSColor(patternImage: Self.noise).setFill(); bounds.fill() }
        NSColor.textBackgroundColor.setFill()
        NSBezierPath(roundedRect: NSRect(x: 88, y: 12, width: max(0, bounds.width-100),
            height: max(0, bounds.height-24)), xRadius: 8, yRadius: 8).fill()
        NSGraphicsContext.restoreGraphicsState()
    }
}

private struct AppearanceSurface: View {
    @ObservedObject var state: AppearanceState

    private static let presets: [(name: String, colors: [Color])] = [
        ("Prism", [rgb(0x55418a), rgb(0xb697ff), rgb(0xb7eeff)]),
        ("Ion", [rgb(0x277294), rgb(0x7addf1)]),
        ("Aurora", [rgb(0x327b71), rgb(0xace3c6)]),
        ("Ember", [rgb(0x9a4e60), rgb(0xf6b48f)]),
        ("Orbit", [rgb(0x454b63)]),
        ("Frost", [rgb(0xb4bed3), rgb(0xe4edf8)])
    ]

    private static func rgb(_ hex: UInt32) -> Color {
        Color(red: Double(hex >> 16 & 255) / 255,
              green: Double(hex >> 8 & 255) / 255,
              blue: Double(hex & 255) / 255)
    }

    var body: some View {
        ScrollView {
        VStack(alignment: .leading, spacing: 20) {
            Text("Make Xenon yours").font(.system(size: 22, weight: .semibold))
            Text("Colors apply to this profile. Spacing applies to all windows.")
                .font(.caption).foregroundStyle(.secondary)
            MaterialPreview(colors: state.colors, intensity: state.intensity,
                grain: state.grain, scheme: state.scheme)
                .frame(height: 110).accessibilityLabel("Browser theme preview")
            Picker("Appearance", selection: $state.scheme) {
                Text("System").tag(0); Text("Light").tag(1); Text("Dark").tag(2)
            }.pickerStyle(.segmented).onChange(of: state.scheme) { state.event("scheme", String($0)) }
            HStack(spacing: 8) {
                ForEach(Self.presets.indices, id: \.self) { index in
                    let preset = Self.presets[index]
                    Button { state.colors = preset.colors } label: {
                        VStack(spacing: 4) {
                            Circle()
                                .fill(LinearGradient(colors: preset.colors,
                                    startPoint: .topLeading, endPoint: .bottomTrailing))
                                .frame(width: 30, height: 30)
                            Text(preset.name).font(.caption)
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(preset.name)
                }
            }
            HStack {
                ForEach(state.colors.indices, id: \.self) { i in
                    ColorPicker("Color \(i + 1)", selection: $state.colors[i], supportsOpacity: false)
                }
                Spacer()
                Button { if state.colors.count < 3 { state.colors.append(state.colors.last ?? .gray); state.saveColors() } } label: { Image(systemName: "plus") }
                    .disabled(state.colors.count == 3).help("Add gradient color")
                Button { if state.colors.count > 1 { state.colors.removeLast(); state.saveColors() } } label: { Image(systemName: "minus") }
                    .disabled(state.colors.count == 1).help("Remove gradient color")
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
            if #available(macOS 14.0, *) {
                Button("Set up iCloud Passwords…") { state.event("icloud", "") }
                    .help("Install Apple's official extension, then authorize it through macOS Passwords.")
            } else {
                Text("iCloud Passwords requires macOS Sonoma or later.").font(.caption)
            }
            Toggle("Online search suggestions", isOn: $state.suggestions)
                .help("Send typed queries to your default search engine. Private windows stay local.")
                .onChange(of: state.suggestions) { state.event("suggestions", String($0)) }
            HStack {
                Button("Reset appearance") { state.event("reset", ""); state.event("close", "") }
                Spacer()
                Button("Done") { state.event("close", "") }.keyboardShortcut(.defaultAction)
            }
        }.padding(24)
        }.frame(width: 480).background(.regularMaterial)
    }
}
@objc(HeliumAppearanceHost) public final class HeliumAppearanceHost: NSObject {
    @objc public let view: NSView
    @objc(initWithValues:event:) public init(values: [String: String], event: @escaping (String, String) -> Void) {
        view = NSHostingView(rootView: AppearanceSurface(state: AppearanceState(values: values, event: event)))
        super.init()
    }
}

// Compact address presentation. Full URL is available in the tooltip and editor.
private final class AddressState: ObservableObject {
    @Published var title = "Search or Enter URL…"
    @Published var url = ""
    var event: (Int) -> Void
    init(event: @escaping (Int) -> Void) { self.event = event }
}
private struct AddressSurface: View {
    @ObservedObject var state: AddressState
    var body: some View {
        HStack(spacing: 4) {
            if state.title != "Search or Enter URL…" {
                Button { state.event(1) } label: {
                    Image(systemName: "slider.horizontal.3").font(.system(size: 12))
                        .frame(width: 24, height: 28).contentShape(Rectangle())
                }.help("Site information and permissions")
                    .accessibilityLabel("Site information and permissions")
            }
            Button { state.event(0) } label: {
                Text(state.title).font(.system(size: 13, weight: .medium)).lineLimit(1)
                    .padding(.horizontal, 4).frame(height: 28).contentShape(Rectangle())
            }.help(state.url).accessibilityLabel("Address: " + state.title)
                .accessibilityHint("Open the centered address editor")
        }
        .buttonStyle(.plain)
        .frame(maxWidth: 280)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .ignoresSafeArea(.container, edges: .vertical)
    }
}
@objc(XenonAddressHost) public final class XenonAddressHost: NSObject {
    private let state: AddressState
    @objc public let view: NSView
    @objc(initWithEvent:) public init(event: @escaping (Int) -> Void) {
        let state = AddressState(event: event)
        self.state = state
        view = ClearHostingView(rootView: AddressSurface(state: state))
        super.init()
    }
    @objc public func invalidate() { state.event = { _ in } }
    @objc(updateWithTitle:url:) public func update(title: String, url: String) {
        if state.title != title { state.title = title }
        if state.url != url { state.url = url }
    }
}

private struct SidebarHeader: View {
    let state: AddressState

    var body: some View {
        GeometryReader { geometry in
            if geometry.size.width >= 112 {
                HStack(spacing: 8) {
                    Text("Tabs").font(.subheadline.weight(.semibold))
                        .accessibilityAddTraits(.isHeader)
                    Spacer(minLength: 4)
                    Button { state.event(4) } label: {
                        Image(systemName: "book")
                    }.help("Bookmarks").accessibilityLabel("Bookmarks")
                    pinButton
                }
                .padding(.horizontal, 10)
                .frame(height: geometry.size.height)
            } else {
                pinButton.frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .buttonStyle(.plain)
    }

    private var pinButton: some View {
        Button { state.event(3) } label: {
            Image(systemName: "pin").frame(width: 22, height: 24)
                .contentShape(Rectangle())
        }.help("Keep sidebar open").accessibilityLabel("Keep sidebar open")
    }
}

private struct SidebarFooter: View {
    @ObservedObject var state: AddressState
    var body: some View {
        GeometryReader { geometry in
            HStack(spacing: 4) {
                if geometry.size.width >= 96 {
                    footerButton("Appearance", symbol: "paintpalette", action: 0)
                    footerButton("Downloads", symbol: "arrow.down.circle", action: 1)
                    footerButton("Settings", symbol: "gearshape", action: 2)
                    Spacer(minLength: 0)
                } else {
                    Menu {
                        Button("Appearance") { state.event(0) }
                        Button("Downloads") { state.event(1) }
                        Button("Settings") { state.event(2) }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .accessibilityLabel("Sidebar tools")
                    }
                    .menuStyle(.borderlessButton)
                    .menuIndicator(.hidden)
                    .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 4)
            .frame(height: geometry.size.height)
        }
    }

    private func footerButton(_ title: String, symbol: String, action: Int) -> some View {
        Button { state.event(action) } label: {
            Image(systemName: symbol)
                .frame(width: 26, height: 28).contentShape(Rectangle())
        }.help(title).accessibilityLabel(title)
    }
}
@objc(XenonSidebarFooterHost) public final class XenonSidebarFooterHost: NSObject {
    private let state: AddressState
    @objc public let view: NSView
    @objc(initWithHeader:event:) public init(header: Bool, event: @escaping (Int) -> Void) {
        let state = AddressState(event: event)
        self.state = state
        if header {
            view = ClearHostingView(rootView: SidebarHeader(state: state))
        } else {
            view = ClearHostingView(rootView: SidebarFooter(state: state))
        }
        super.init()
    }
    @objc public func invalidate() { state.event = { _ in } }
}

private struct HomeSurface: View {
    @ObservedObject var state: AddressState
    var body: some View {
        Color.clear.frame(maxWidth: .infinity, maxHeight: .infinity)
            .accessibilityLabel("Home. Use Command T to search or open a page.")
    }
}
@objc(XenonHomeHost) public final class XenonHomeHost: NSObject {
    private let state: AddressState
    @objc public let view: NSView
    @objc(initWithEvent:) public init(event: @escaping () -> Void) {
        let state = AddressState(event: { _ in event() })
        self.state = state
        view = ClearHostingView(rootView: HomeSurface(state: state))
        super.init()
    }
    @objc public func invalidate() { state.event = { _ in } }
}
