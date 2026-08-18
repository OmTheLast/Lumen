import Cocoa
import WebKit

final class WindowDelegate: NSObject, NSWindowDelegate {
    func windowWillClose(_ notification: Notification) {
        NSApp.terminate(nil)
    }
}

func parseURL() -> URL {
    let args = CommandLine.arguments
    var index = 1
    while index < args.count {
        if args[index] == "--url", index + 1 < args.count, let url = URL(string: args[index + 1]) {
            return url
        }
        index += 1
    }
    return URL(string: "http://127.0.0.1:8765")!
}

let url = parseURL()
let app = NSApplication.shared
app.setActivationPolicy(.regular)

let configuration = WKWebViewConfiguration()
configuration.preferences.javaScriptCanOpenWindowsAutomatically = true

let screenFrame = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
let width = min(max(screenFrame.width * 0.82, 1040), 1440)
let height = min(max(screenFrame.height * 0.82, 720), 980)
let frame = NSRect(
    x: screenFrame.midX - width / 2,
    y: screenFrame.midY - height / 2,
    width: width,
    height: height
)

let window = NSWindow(
    contentRect: frame,
    styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
    backing: .buffered,
    defer: false
)
window.title = "Lumen"
window.titlebarAppearsTransparent = true
window.isMovableByWindowBackground = true
window.minSize = NSSize(width: 920, height: 620)
window.backgroundColor = NSColor(calibratedRed: 0.02, green: 0.012, blue: 0.008, alpha: 1.0)

let webView = WKWebView(frame: NSRect(x: 0, y: 0, width: frame.width, height: frame.height), configuration: configuration)
webView.autoresizingMask = [.width, .height]
webView.setValue(false, forKey: "drawsBackground")
webView.load(URLRequest(url: url))

let delegate = WindowDelegate()
window.delegate = delegate
window.contentView = webView
window.center()
window.makeKeyAndOrderFront(nil)
app.activate(ignoringOtherApps: true)
app.run()
