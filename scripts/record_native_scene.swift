import AppKit
import AVFoundation
import ScreenCaptureKit

// Capture only IW4L, including its audio. The scene log supplies trim boundaries.
final class Recorder: NSObject, SCRecordingOutputDelegate, SCStreamDelegate, SCStreamOutput, @unchecked Sendable {
    var finished = false
    var failure: Error?
    var firstPTS: Double?
    func recordingOutputDidStartRecording(_ output: SCRecordingOutput) {
        print("Native window recording started")
        fflush(stdout)
    }
    func recordingOutputDidFinishRecording(_ output: SCRecordingOutput) { finished = true }
    func recordingOutput(_ output: SCRecordingOutput, didFailWithError error: Error) { failure = error }
    func stream(_ stream: SCStream, didStopWithError error: Error) { failure = error }
    func stream(_ stream: SCStream, didOutputSampleBuffer sample: CMSampleBuffer, of type: SCStreamOutputType) {
        if type == .screen && firstPTS == nil && sample.isValid {
            firstPTS = sample.presentationTimeStamp.seconds
        }
    }
}

@main struct Main {
    @MainActor static func main() async {
        do { try await record() }
        catch { fputs("Native recording failed: \(error.localizedDescription)\n", stderr); exit(1) }
    }
    @MainActor static func record() async throws {
        guard (3...4).contains(CommandLine.arguments.count) else {
            print("Usage: record-native-scene PROJECT_ROOT OUTPUT.mp4 [SCENE.json]")
            return
        }
        let root = URL(fileURLWithPath: CommandLine.arguments[1])
        let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
        let scene = CommandLine.arguments.count == 4
            ? URL(fileURLWithPath: CommandLine.arguments[3])
            : root.appendingPathComponent("local-assets/scenes/worlds-collide-native.json")
        let log = root.appendingPathComponent("local-runs/cinema/iw4l-artifacts/logs/latest.log")
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: false)
        guard let window = content.windows.first(where: {
            $0.owningApplication?.applicationName.lowercased().contains("iw4l") == true && $0.frame.width > 500
        }) else { throw NSError(domain: "NativeCapture", code: 1, userInfo: [NSLocalizedDescriptionKey: "IW4L game window was not found."]) }
        if let pid = window.owningApplication?.processID {
            NSRunningApplication(processIdentifier: pid)?.activate()
        }
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        config.width = 1280
        config.height = 720
        config.minimumFrameInterval = CMTime(value: 1, timescale: 60)
        config.queueDepth = 5
        config.showsCursor = false
        config.ignoreShadowsSingleWindow = true
        config.ignoreGlobalClipSingleWindow = true
        config.capturesAudio = true
        config.captureMicrophone = false
        config.sampleRate = 48000
        config.channelCount = 2
        config.captureDynamicRange = .SDR
        let delegate = Recorder()
        let stream = SCStream(filter: filter, configuration: config, delegate: delegate)
        try stream.addStreamOutput(delegate, type: .screen, sampleHandlerQueue: .main)
        let recordingConfig = SCRecordingOutputConfiguration()
        recordingConfig.outputURL = outputURL
        recordingConfig.videoCodecType = .h264
        recordingConfig.outputFileType = .mp4
        let recording = SCRecordingOutput(configuration: recordingConfig, delegate: delegate)
        try stream.addRecordingOutput(recording)
        try await stream.startCapture()
        try await Task.sleep(for: .milliseconds(500))
        let handle = try FileHandle(forReadingFrom: log)
        try handle.seekToEnd()
        try FileManager.default.setAttributes([.modificationDate: Date()], ofItemAtPath: scene.path)
        var start: Double?
        var end: Double?
        var pending = ""
        let deadline = Date().addingTimeInterval(60)
        while Date() < deadline && end == nil {
            if let error = delegate.failure { throw error }
            if let data = try handle.readToEnd(), !data.isEmpty {
                pending += String(decoding: data, as: UTF8.self)
                while let newline = pending.firstIndex(of: "\n") {
                    let line = String(pending[..<newline])
                    pending.removeSubrange(...newline)
                    let now = CMClockGetTime(CMClockGetHostTimeClock()).seconds
                    if line.contains("CINEMA V2:") { start = now; print("Take started"); fflush(stdout) }
                    if start != nil && line.contains("CINEMA COMPLETE:") { end = now }
                }
            }
            try await Task.sleep(for: .milliseconds(10))
        }
        try await Task.sleep(for: .milliseconds(250))
        try await stream.stopCapture()
        for _ in 0..<100 where !delegate.finished && delegate.failure == nil {
            try await Task.sleep(for: .milliseconds(50))
        }
        if let error = delegate.failure { throw error }
        guard delegate.finished, let start, let end, let first = delegate.firstPTS else {
            throw NSError(domain: "NativeCapture", code: 2, userInfo: [NSLocalizedDescriptionKey: "Recording or scene did not complete; raw capture retained."])
        }
        let metadata: [String: Any] = ["trim_start_seconds": max(0, start - first), "take_duration_seconds": end - start,
            "window_id": window.windowID, "width": config.width, "height": config.height,
            "audio": "IW4L application audio; no microphone", "raw_file": outputURL.path]
        try JSONSerialization.data(withJSONObject: metadata, options: [.prettyPrinted, .sortedKeys])
            .write(to: outputURL.deletingPathExtension().appendingPathExtension("json"))
        print("Recorded \(end - start)s native take; trim starts at \(start - first)s")
    }
}
