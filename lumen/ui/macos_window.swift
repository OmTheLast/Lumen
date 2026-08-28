import Cocoa
import AVFoundation
import Speech
import WebKit

final class WindowDelegate: NSObject, NSWindowDelegate {
    private let backend: BackendController?

    init(backend: BackendController?) {
        self.backend = backend
    }

    func windowWillClose(_ notification: Notification) {
        backend?.stop()
        NSApp.terminate(nil)
    }
}

final class BackendController {
    private var process: Process?

    func startIfNeeded() {
        guard process == nil else { return }
        guard let repoURL = findRepositoryURL() else { return }

        let logURL = FileManager.default
            .homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/Lumen/lumen.log")
        try? FileManager.default.createDirectory(
            at: logURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }

        let logHandle = try? FileHandle(forWritingTo: logURL)
        logHandle?.seekToEndOfFile()

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        proc.arguments = ["uv", "run", "python", "-m", "lumen.main", "--app"]
        proc.currentDirectoryURL = repoURL

        var environment = ProcessInfo.processInfo.environment
        environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (environment["PATH"] ?? "")
        environment["LUMEN_REPO_DIR"] = repoURL.path
        environment["LUMEN_UI_OPEN_BROWSER"] = environment["LUMEN_UI_OPEN_BROWSER"] ?? "0"
        environment["LUMEN_APP_WINDOW_ENABLED"] = "0"
        environment["LUMEN_OVERLAY_ENABLED"] = environment["LUMEN_OVERLAY_ENABLED"] ?? "1"
        proc.environment = environment
        proc.standardOutput = logHandle
        proc.standardError = logHandle

        do {
            try proc.run()
            process = proc
        } catch {
            process = nil
        }
    }

    func stop() {
        guard let process else { return }
        if process.isRunning {
            process.terminate()
            DispatchQueue.global().asyncAfter(deadline: .now() + 1.0) {
                if process.isRunning {
                    process.interrupt()
                }
            }
        }
        self.process = nil
    }

    private func findRepositoryURL() -> URL? {
        let env = ProcessInfo.processInfo.environment
        if let repo = env["LUMEN_REPO_DIR"], !repo.isEmpty {
            return URL(fileURLWithPath: repo)
        }

        if
            let resourceURL = Bundle.main.resourceURL,
            let contents = try? String(contentsOf: resourceURL.appendingPathComponent("repo-path.txt"), encoding: .utf8)
        {
            let repo = contents.trimmingCharacters(in: .whitespacesAndNewlines)
            if !repo.isEmpty {
                return URL(fileURLWithPath: repo)
            }
        }

        return nil
    }
}

final class NativeVoiceController: NSObject, WKScriptMessageHandler {
    private enum ListenMode {
        case wake
        case command
        case manual
    }

    private weak var webView: WKWebView?
    private let baseURL: URL
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    private var isRecording = false
    private var listenMode: ListenMode?
    private var wakeModeEnabled = true

    init(webView: WKWebView, baseURL: URL) {
        self.webView = webView
        self.baseURL = baseURL
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        if isRecording {
            stop(restartWake: true)
        } else {
            requestPermissionsThenStart(.manual)
        }
    }

    func startWakeMode() {
        wakeModeEnabled = true
        requestPermissionsThenStart(.wake)
    }

    private func requestPermissionsThenStart(_ mode: ListenMode) {
        guard Bundle.main.object(forInfoDictionaryKey: "NSSpeechRecognitionUsageDescription") != nil else {
            setStatus("Native voice requires Lumen.app.")
            return
        }
        setStatus("Requesting microphone permission.")
        SFSpeechRecognizer.requestAuthorization { [weak self] speechStatus in
            AVCaptureDevice.requestAccess(for: .audio) { micAllowed in
                DispatchQueue.main.async {
                    guard let self else { return }
                    guard speechStatus == .authorized && micAllowed else {
                        self.setRecording(false)
                        self.setStatus("Native voice permission denied.")
                        return
                    }
                    self.start(mode)
                }
            }
        }
    }

    private func start(_ mode: ListenMode) {
        guard !isRecording else { return }
        guard let recognizer, recognizer.isAvailable else {
            setStatus("Native speech recognition unavailable.")
            return
        }

        task?.cancel()
        task = nil

        request = SFSpeechAudioBufferRecognitionRequest()
        request?.shouldReportPartialResults = true
        request?.requiresOnDeviceRecognition = false

        let input = audioEngine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            self?.request?.append(buffer)
        }

        do {
            audioEngine.prepare()
            try audioEngine.start()
        } catch {
            setStatus("Could not start microphone.")
            return
        }

        isRecording = true
        listenMode = mode
        setRecording(true)
        switch mode {
        case .wake:
            setStatus("Wake word armed. Say Lumen.")
        case .command:
            setStatus("Lumen awake. Say the command.")
        case .manual:
            setStatus("Native voice recognition active.")
        }

        task = recognizer.recognitionTask(with: request!) { [weak self] result, error in
            guard let self else { return }
            if let text = result?.bestTranscription.formattedString.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
                self.handleTranscript(text, isFinal: result?.isFinal == true)
            }
            if error != nil {
                self.stop(restartWake: self.wakeModeEnabled)
                self.setStatus("Native voice recognition restarted.")
            }
        }
    }

    private func handleTranscript(_ text: String, isFinal: Bool) {
        switch listenMode {
        case .wake:
            if let command = commandAfterWakeWord(in: text) {
                setTranscript("Lumen")
                if command.isEmpty {
                    switchToCommandMode()
                } else {
                    finish(command: command)
                }
                return
            }
            if isFinal {
                restartWakeRecognition()
            }
        case .command:
            setTranscript(text)
            if isFinal {
                finish(command: text)
            }
        case .manual:
            setTranscript(text)
            if isFinal {
                finish(command: text)
            }
        case nil:
            return
        }
    }

    private func commandAfterWakeWord(in text: String) -> String? {
        let lowered = text.lowercased()
        guard let range = lowered.range(of: "lumen") else {
            return nil
        }
        let commandStart = text.index(text.startIndex, offsetBy: lowered.distance(from: lowered.startIndex, to: range.upperBound))
        return text[commandStart...]
            .trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(.punctuationCharacters))
    }

    private func switchToCommandMode() {
        stop(restartWake: false)
        setStatus("Lumen awake. Say the command.")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { [weak self] in
            self?.requestPermissionsThenStart(.command)
        }
    }

    private func restartWakeRecognition() {
        stop(restartWake: false)
        scheduleWakeRestart()
    }

    private func scheduleWakeRestart(delay: TimeInterval = 0.35) {
        guard wakeModeEnabled else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self, !self.isRecording else { return }
            self.requestPermissionsThenStart(.wake)
        }
    }

    private func finish(command: String) {
        let trimmed = command.trimmingCharacters(in: .whitespacesAndNewlines)
        stop(restartWake: false)
        if !trimmed.isEmpty {
            postCommand(trimmed)
        }
        scheduleWakeRestart(delay: 1.0)
    }

    private func stop(restartWake: Bool) {
        guard isRecording else {
            if restartWake {
                scheduleWakeRestart()
            }
            return
        }
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        task?.cancel()
        request = nil
        task = nil
        isRecording = false
        listenMode = nil
        setRecording(false)
        if restartWake {
            scheduleWakeRestart()
        }
    }

    private func postCommand(_ command: String) {
        setTranscript(command)
        setStatus("Wake command sent to Lumen.")
        var request = URLRequest(url: baseURL.appendingPathComponent("chat"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["text": command])
        URLSession.shared.dataTask(with: request) { [weak self] _, _, _ in
            DispatchQueue.main.async {
                self?.evaluate("refreshChat();")
            }
        }.resume()
    }

    private func setRecording(_ active: Bool) {
        evaluate("document.getElementById('voiceButton')?.classList.\(active ? "add" : "remove")('recording');")
    }

    private func setTranscript(_ text: String) {
        setElementText(id: "transcript", text: text)
    }

    private func setStatus(_ text: String) {
        setElementText(id: "modelStatus", text: text)
    }

    private func setElementText(id: String, text: String) {
        guard
            let data = try? JSONSerialization.data(withJSONObject: text, options: [.fragmentsAllowed]),
            let encoded = String(data: data, encoding: .utf8)
        else { return }
        evaluate("document.getElementById('\(id)').textContent = \(encoded);")
    }

    private func evaluate(_ script: String) {
        webView?.evaluateJavaScript(script)
    }
}

final class WebViewReadyDelegate: NSObject, WKNavigationDelegate {
    private let onReady: () -> Void

    init(onReady: @escaping () -> Void) {
        self.onReady = onReady
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        onReady()
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

func hasURLArgument() -> Bool {
    CommandLine.arguments.contains("--url")
}

func loadWhenReady(webView: WKWebView, url: URL, remainingAttempts: Int = 40) {
    var request = URLRequest(url: url.appendingPathComponent("state"))
    request.timeoutInterval = 0.4
    URLSession.shared.dataTask(with: request) { _, response, _ in
        let ready = (response as? HTTPURLResponse)?.statusCode == 200
        DispatchQueue.main.async {
            if ready || remainingAttempts <= 0 {
                webView.load(URLRequest(url: url))
            } else {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
                    loadWhenReady(webView: webView, url: url, remainingAttempts: remainingAttempts - 1)
                }
            }
        }
    }.resume()
}

let url = parseURL()
let backend = hasURLArgument() ? nil : BackendController()
backend?.startIfNeeded()

let app = NSApplication.shared
app.setActivationPolicy(.regular)

let configuration = WKWebViewConfiguration()
configuration.preferences.javaScriptCanOpenWindowsAutomatically = true
let userContentController = WKUserContentController()
let nativeVoiceScript = """
window.lumenNativeVoice = {
  available: true,
  toggle: function () {
    window.webkit.messageHandlers.lumenVoice.postMessage({ type: "toggle" });
  }
};
"""
userContentController.addUserScript(WKUserScript(source: nativeVoiceScript, injectionTime: .atDocumentStart, forMainFrameOnly: true))
configuration.userContentController = userContentController

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

let delegate = WindowDelegate(backend: backend)
let voiceController = NativeVoiceController(webView: webView, baseURL: url)
let navigationDelegate = WebViewReadyDelegate {
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
        voiceController.startWakeMode()
    }
}
userContentController.add(voiceController, name: "lumenVoice")
webView.navigationDelegate = navigationDelegate
window.delegate = delegate
window.contentView = webView
window.center()
window.makeKeyAndOrderFront(nil)
app.activate(ignoringOtherApps: true)
loadWhenReady(webView: webView, url: url)
app.run()
