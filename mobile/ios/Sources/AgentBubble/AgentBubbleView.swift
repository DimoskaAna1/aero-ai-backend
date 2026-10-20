import AVFoundation
import Speech
import UIKit

/// Floating bubble for a host iOS app. It posts to the same chat API as the web widget.
public final class AgentBubbleView: UIView, SFSpeechRecognizerDelegate {
    private let apiBase: String
    private let tenantId: String
    private let tenantKey: String
    private let sessionId = "sess_" + UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(16)
    private let log = UITextView()
    private let field = UITextField()
    private let panel = UIView()
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "mk-MK"))
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    public init(apiBase: String, tenantId: String, tenantKey: String) {
        self.apiBase = apiBase
        self.tenantId = tenantId
        self.tenantKey = tenantKey
        super.init(frame: .zero)
        build()
    }

    required init?(coder: NSCoder) {
        return nil
    }

    private func build() {
        let bubble = UIButton(type: .system)
        bubble.setTitle("Ana", for: .normal)
        bubble.backgroundColor = UIColor(red: 0.22, green: 0.74, blue: 0.97, alpha: 1)
        bubble.setTitleColor(UIColor(red: 0.02, green: 0.06, blue: 0.09, alpha: 1), for: .normal)
        bubble.layer.cornerRadius = 28
        bubble.translatesAutoresizingMaskIntoConstraints = false
        bubble.addTarget(self, action: #selector(toggle), for: .touchUpInside)
        addSubview(bubble)

        panel.backgroundColor = UIColor(red: 0.06, green: 0.09, blue: 0.16, alpha: 1)
        panel.layer.cornerRadius = 18
        panel.isHidden = true
        panel.translatesAutoresizingMaskIntoConstraints = false
        addSubview(panel)

        log.backgroundColor = .clear
        log.textColor = UIColor(red: 0.91, green: 0.95, blue: 1, alpha: 1)
        log.isEditable = false
        log.text = "Zdravo. Prasaj za proizvod, cena ili termin."
        log.translatesAutoresizingMaskIntoConstraints = false
        panel.addSubview(log)

        field.placeholder = "Poraka"
        field.textColor = .white
        field.borderStyle = .roundedRect
        field.translatesAutoresizingMaskIntoConstraints = false
        panel.addSubview(field)

        let send = UIButton(type: .system)
        send.setTitle("Send", for: .normal)
        send.addTarget(self, action: #selector(sendText), for: .touchUpInside)
        send.translatesAutoresizingMaskIntoConstraints = false
        panel.addSubview(send)

        let mic = UIButton(type: .system)
        mic.setTitle("Mic", for: .normal)
        mic.addTarget(self, action: #selector(listen), for: .touchUpInside)
        mic.translatesAutoresizingMaskIntoConstraints = false
        panel.addSubview(mic)

        NSLayoutConstraint.activate([
            bubble.widthAnchor.constraint(equalToConstant: 56),
            bubble.heightAnchor.constraint(equalToConstant: 56),
            bubble.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -16),
            bubble.bottomAnchor.constraint(equalTo: bottomAnchor, constant: -16),
            panel.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 16),
            panel.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -16),
            panel.bottomAnchor.constraint(equalTo: bubble.topAnchor, constant: -12),
            panel.heightAnchor.constraint(equalToConstant: 360),
            log.topAnchor.constraint(equalTo: panel.topAnchor, constant: 12),
            log.leadingAnchor.constraint(equalTo: panel.leadingAnchor, constant: 12),
            log.trailingAnchor.constraint(equalTo: panel.trailingAnchor, constant: -12),
            log.bottomAnchor.constraint(equalTo: field.topAnchor, constant: -8),
            field.leadingAnchor.constraint(equalTo: panel.leadingAnchor, constant: 12),
            field.bottomAnchor.constraint(equalTo: panel.bottomAnchor, constant: -12),
            field.trailingAnchor.constraint(equalTo: mic.leadingAnchor, constant: -8),
            mic.centerYAnchor.constraint(equalTo: field.centerYAnchor),
            mic.trailingAnchor.constraint(equalTo: send.leadingAnchor, constant: -8),
            send.centerYAnchor.constraint(equalTo: field.centerYAnchor),
            send.trailingAnchor.constraint(equalTo: panel.trailingAnchor, constant: -12),
        ])
    }

    @objc private func toggle() {
        panel.isHidden.toggle()
    }

    @objc private func sendText() {
        let text = field.text?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !text.isEmpty else { return }
        field.text = ""
        ask(text)
    }

    @objc private func listen() {
        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            guard status == .authorized else { return }
            DispatchQueue.main.async { self?.startRecognition() }
        }
    }

    private func startRecognition() {
        request?.endAudio()
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        let next = SFSpeechAudioBufferRecognitionRequest()
        request = next
        let node = audioEngine.inputNode
        let format = node.outputFormat(forBus: 0)
        node.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            next.append(buffer)
        }
        audioEngine.prepare()
        try? audioEngine.start()
        task = recognizer?.recognitionTask(with: next) { [weak self] result, _ in
            guard let said = result?.bestTranscription.formattedString, result?.isFinal == true else { return }
            self?.audioEngine.stop()
            self?.ask(said)
        }
    }

    private func ask(_ text: String) {
        append("You: \(text)")
        let base = apiBase.hasSuffix("/") ? String(apiBase.dropLast()) : apiBase
        var request = URLRequest(url: URL(string: base + "/api/v1/chat")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(tenantId, forHTTPHeaderField: "X-Tenant-Id")
        request.setValue(tenantKey, forHTTPHeaderField: "X-Tenant-Key")
        let body: [String: String] = [
            "tenant_id": tenantId,
            "user_message": text,
            "session_id": String(sessionId),
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        URLSession.shared.dataTask(with: request) { [weak self] data, _, _ in
            let reply = Self.readMessage(data)
            DispatchQueue.main.async { self?.append("Ana: \(reply)") }
        }.resume()
    }

    private static func readMessage(_ data: Data?) -> String {
        guard let data = data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return "The assistant is unavailable right now."
        }
        if let message = json["assistant_message"] as? String, !message.isEmpty {
            return message
        }
        if let detail = json["detail"] as? String {
            return detail
        }
        return "The assistant is unavailable right now."
    }

    private func append(_ line: String) {
        log.text = (log.text ?? "") + "\n\n" + line
    }
}
