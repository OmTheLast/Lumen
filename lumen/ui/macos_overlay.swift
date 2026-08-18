import Cocoa
import Foundation

struct LumenState {
    var state: String = "idle"
    var message: String = "Lumen is running."
}

final class StatePoller {
    private let url: URL
    private weak var view: OrbView?
    private var timer: Timer?

    init(url: URL, view: OrbView) {
        self.url = url
        self.view = view
    }

    func start() {
        fetch()
        timer = Timer.scheduledTimer(withTimeInterval: 0.45, repeats: true) { [weak self] _ in
            self?.fetch()
        }
    }

    private func fetch() {
        URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            guard let self, let data else {
                DispatchQueue.main.async {
                    self?.view?.lumenState = LumenState(state: "offline", message: "Reconnecting")
                }
                return
            }

            let payload = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            let state = payload?["state"] as? String ?? "idle"
            let message = payload?["message"] as? String ?? "Lumen is running."
            DispatchQueue.main.async {
                self.view?.lumenState = LumenState(state: state, message: message)
            }
        }.resume()
    }
}

final class OrbView: NSView {
    var lumenState = LumenState() {
        didSet { needsDisplay = true }
    }

    private var displayLink: Timer?
    private let nodes: [SIMD3<Double>] = OrbView.makeNodes()

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
        displayLink = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            self?.needsDisplay = true
        }
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override var isOpaque: Bool { false }

    override func draw(_ dirtyRect: NSRect) {
        guard let ctx = NSGraphicsContext.current?.cgContext else { return }
        ctx.clear(bounds)

        let time = Date().timeIntervalSinceReferenceDate
        let color = palette(for: lumenState.state)
        let size = min(bounds.width, bounds.height)
        let center = CGPoint(x: bounds.midX, y: bounds.midY)
        let radius = size * 0.31
        let pulse = lumenState.state == "idle" ? 1.0 : 1.0 + sin(time * 6.0) * 0.035
        let outer = radius * pulse

        drawGlow(ctx, center: center, radius: outer, color: color)
        drawSpokes(ctx, center: center, radius: outer, color: color, time: time)
        drawNetwork(ctx, center: center, radius: outer, color: color, time: time)
        drawCore(ctx, center: center, radius: outer, color: color, time: time)
        drawStatusDot(ctx, color: color)
    }

    private func drawGlow(_ ctx: CGContext, center: CGPoint, radius: CGFloat, color: NSColor) {
        let cgColor = color.cgColor
        let glow = CGGradient(
            colorsSpace: CGColorSpaceCreateDeviceRGB(),
            colors: [
                color.withAlphaComponent(0.46).cgColor,
                color.withAlphaComponent(0.12).cgColor,
                NSColor.clear.cgColor
            ] as CFArray,
            locations: [0.0, 0.48, 1.0]
        )
        if let glow {
            ctx.drawRadialGradient(
                glow,
                startCenter: center,
                startRadius: 0,
                endCenter: center,
                endRadius: radius * 1.36,
                options: []
            )
        }

        ctx.setStrokeColor(color.withAlphaComponent(0.78).cgColor)
        ctx.setLineWidth(1.6)
        ctx.strokeEllipse(in: CGRect(x: center.x - radius, y: center.y - radius, width: radius * 2, height: radius * 2))

        ctx.setStrokeColor(cgColor.copy(alpha: 0.24) ?? cgColor)
        ctx.setLineWidth(0.8)
        ctx.strokeEllipse(
            in: CGRect(
                x: center.x - radius * 1.18,
                y: center.y - radius * 1.18,
                width: radius * 2.36,
                height: radius * 2.36
            )
        )
    }

    private func drawSpokes(_ ctx: CGContext, center: CGPoint, radius: CGFloat, color: NSColor, time: Double) {
        for index in 0..<28 {
            let angle = Double(index) / 28.0 * .pi * 2.0 + time * 0.9
            let inner = radius * (index % 2 == 0 ? 0.68 : 0.78)
            let outer = radius * (index % 3 == 0 ? 1.1 : 1.02)
            let alpha: CGFloat = index % 3 == 0 ? 0.54 : 0.2
            ctx.setStrokeColor(color.withAlphaComponent(alpha).cgColor)
            ctx.setLineWidth(index % 4 == 0 ? 1.4 : 0.8)
            ctx.move(to: CGPoint(x: center.x + cos(angle) * inner, y: center.y + sin(angle) * inner))
            ctx.addLine(to: CGPoint(x: center.x + cos(angle) * outer, y: center.y + sin(angle) * outer))
            ctx.strokePath()
        }
    }

    private func drawNetwork(_ ctx: CGContext, center: CGPoint, radius: CGFloat, color: NSColor, time: Double) {
        let projected = nodes.map { project($0, center: center, radius: radius, time: time) }

        for i in projected.indices {
            for j in (i + 1)..<projected.count {
                let a = projected[i]
                let b = projected[j]
                let dist = hypot(a.raw.x - b.raw.x, hypot(a.raw.y - b.raw.y, a.raw.z - b.raw.z))
                if dist > 0.42 { continue }
                let depth = max(0.16, min(0.62, CGFloat((a.z + b.z + 2.0) / 5.2)))
                ctx.setStrokeColor(color.withAlphaComponent(depth).cgColor)
                ctx.setLineWidth(0.55)
                ctx.move(to: a.point)
                ctx.addLine(to: b.point)
                ctx.strokePath()
            }
        }

        for item in projected.sorted(by: { $0.z < $1.z }) {
            let alpha = max(0.28, min(0.92, CGFloat((item.z + 1.2) / 2.3)))
            let nodeRadius = CGFloat(1.15) * item.depth
            ctx.setFillColor(color.withAlphaComponent(alpha).cgColor)
            ctx.fillEllipse(in: CGRect(x: item.point.x - nodeRadius, y: item.point.y - nodeRadius, width: nodeRadius * 2, height: nodeRadius * 2))
        }
    }

    private func drawCore(_ ctx: CGContext, center: CGPoint, radius: CGFloat, color: NSColor, time: Double) {
        let orbit = SIMD3<Double>(
            sin(time * 1.1) * 0.16 + 0.06,
            cos(time * 1.35) * 0.11,
            sin(time * 1.6) * 0.18
        )
        let core = project(orbit, center: center, radius: radius, time: time)
        let coreRadius = radius * 0.18 * core.depth
        let glow = CGGradient(
            colorsSpace: CGColorSpaceCreateDeviceRGB(),
            colors: [
                NSColor.white.withAlphaComponent(0.96).cgColor,
                color.withAlphaComponent(0.78).cgColor,
                NSColor.clear.cgColor
            ] as CFArray,
            locations: [0.0, 0.34, 1.0]
        )
        if let glow {
            ctx.drawRadialGradient(glow, startCenter: core.point, startRadius: 0, endCenter: core.point, endRadius: coreRadius * 2.4, options: [])
        }

        for index in 0..<5 {
            let angle = time * 2.0 + Double(index) * 1.26
            let node = SIMD3<Double>(
                orbit.x + cos(angle) * 0.09,
                orbit.y + sin(angle * 1.2) * 0.07,
                orbit.z + sin(angle) * 0.08
            )
            let p = project(node, center: center, radius: radius, time: time)
            ctx.setStrokeColor(color.withAlphaComponent(0.36).cgColor)
            ctx.setLineWidth(0.8)
            ctx.move(to: core.point)
            ctx.addLine(to: p.point)
            ctx.strokePath()
        }
    }

    private func drawStatusDot(_ ctx: CGContext, color: NSColor) {
        let dot = CGPoint(x: bounds.maxX - 14, y: bounds.minY + 14)
        ctx.setFillColor(NSColor.black.withAlphaComponent(0.48).cgColor)
        ctx.fillEllipse(in: CGRect(x: dot.x - 9, y: dot.y - 9, width: 18, height: 18))
        ctx.setStrokeColor(color.withAlphaComponent(0.82).cgColor)
        ctx.setLineWidth(1.2)
        ctx.strokeEllipse(in: CGRect(x: dot.x - 9, y: dot.y - 9, width: 18, height: 18))
        ctx.setFillColor(color.cgColor)
        ctx.fillEllipse(in: CGRect(x: dot.x - 3.4, y: dot.y - 3.4, width: 6.8, height: 6.8))
    }

    private func project(_ point: SIMD3<Double>, center: CGPoint, radius: CGFloat, time: Double) -> (point: CGPoint, z: Double, depth: CGFloat, raw: SIMD3<Double>) {
        let ay = time * 0.72
        let ax = sin(time * 0.42) * 0.32 + 0.22
        let az = cos(time * 0.31) * 0.12
        var x = point.x
        var y = point.y
        var z = point.z

        var c = cos(ay)
        var s = sin(ay)
        (x, z) = (x * c - z * s, x * s + z * c)
        c = cos(ax)
        s = sin(ax)
        (y, z) = (y * c - z * s, y * s + z * c)
        c = cos(az)
        s = sin(az)
        (x, y) = (x * c - y * s, x * s + y * c)

        let focal = 2.35
        let depth = CGFloat(focal / (focal - z))
        return (
            CGPoint(x: center.x + CGFloat(x) * radius * depth, y: center.y + CGFloat(y) * radius * depth),
            z,
            depth,
            SIMD3<Double>(x, y, z)
        )
    }

    private func palette(for state: String) -> NSColor {
        switch state {
        case "listening": return NSColor(calibratedRed: 1.0, green: 0.76, blue: 0.36, alpha: 1.0)
        case "thinking": return NSColor(calibratedRed: 1.0, green: 0.56, blue: 0.18, alpha: 1.0)
        case "acting": return NSColor(calibratedRed: 1.0, green: 0.42, blue: 0.12, alpha: 1.0)
        case "speaking": return NSColor(calibratedRed: 1.0, green: 0.82, blue: 0.48, alpha: 1.0)
        case "error", "offline": return NSColor(calibratedRed: 1.0, green: 0.4, blue: 0.37, alpha: 1.0)
        default: return NSColor(calibratedRed: 1.0, green: 0.6, blue: 0.21, alpha: 1.0)
        }
    }

    private static func makeNodes() -> [SIMD3<Double>] {
        var nodes: [SIMD3<Double>] = []
        for lat in stride(from: -60.0, through: 60.0, by: 30.0) {
            let phi = lat * .pi / 180.0
            let ringCount = Int((14.0 * cos(phi)).rounded()) + 7
            for index in 0..<ringCount {
                let theta = Double(index) / Double(ringCount) * .pi * 2.0
                nodes.append(SIMD3<Double>(cos(phi) * cos(theta), sin(phi), cos(phi) * sin(theta)))
            }
        }
        for index in 0..<18 {
            let angle = Double(index) * 2.399963
            let z = 1.0 - (2.0 * Double(index) + 1.0) / 18.0
            let r = sqrt(1.0 - z * z) * 0.78
            nodes.append(SIMD3<Double>(cos(angle) * r, sin(angle) * r, z))
        }
        return nodes
    }
}

func parseArgs() -> (URL, CGFloat) {
    var stateURL = URL(string: "http://127.0.0.1:8765/state")!
    var size: CGFloat = 92
    var index = 1
    let args = CommandLine.arguments
    while index < args.count {
        if args[index] == "--state-url", index + 1 < args.count, let url = URL(string: args[index + 1]) {
            stateURL = url
            index += 2
            continue
        }
        if args[index] == "--size", index + 1 < args.count, let value = Double(args[index + 1]) {
            size = max(72, CGFloat(value))
            index += 2
            continue
        }
        index += 1
    }
    return (stateURL, size)
}

let (stateURL, size) = parseArgs()
let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let visibleFrame = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
let frame = NSRect(
    x: visibleFrame.maxX - size - 18,
    y: visibleFrame.minY + 18,
    width: size,
    height: size
)
let window = NSWindow(
    contentRect: frame,
    styleMask: [.borderless],
    backing: .buffered,
    defer: false
)
window.isOpaque = false
window.backgroundColor = .clear
window.hasShadow = false
window.ignoresMouseEvents = true
window.level = .statusBar
window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]

let view = OrbView(frame: NSRect(x: 0, y: 0, width: size, height: size))
window.contentView = view
window.orderFrontRegardless()

let poller = StatePoller(url: stateURL, view: view)
poller.start()

app.run()
