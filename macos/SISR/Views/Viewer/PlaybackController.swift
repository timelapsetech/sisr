import Foundation
import Observation
import SISRKit

enum ViewerZoomMode: String {
    case fit
    case actual
    case double
}

@Observable
@MainActor
final class PlaybackController {
    var isPlaying = false
    var zoomMode: ViewerZoomMode = .fit
    var shuttleRate: Int = 0 // -2…2 via J/K/L

    private var timer: Timer?

    func toggle(project: SequenceProject) {
        if isPlaying {
            stop()
        } else {
            play(project: project)
        }
    }

    func play(project: SequenceProject) {
        stop()
        isPlaying = true
        let fps = max(0.01, project.render.fps)
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / fps, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                let last = max(0, project.frameCount - 1)
                if project.playheadIndex >= last {
                    self.stop()
                    return
                }
                project.playheadIndex = min(last, project.playheadIndex + 1)
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        isPlaying = false
        shuttleRate = 0
    }

    func step(project: SequenceProject, delta: Int) {
        stop()
        let last = max(0, project.frameCount - 1)
        project.playheadIndex = min(last, max(0, project.playheadIndex + delta))
    }

    func shuttle(project: SequenceProject, direction: Int) {
        // J = -1, K = stop, L = +1
        if direction == 0 {
            stop()
            return
        }
        shuttleRate = max(-2, min(2, shuttleRate + direction))
        if shuttleRate == 0 {
            stop()
            return
        }
        stop()
        isPlaying = true
        let rate = shuttleRate
        let baseFPS = max(0.01, project.render.fps)
        let interval = 1.0 / (baseFPS * Double(abs(rate)))
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                let delta = rate > 0 ? 1 : -1
                let last = max(0, project.frameCount - 1)
                let next = project.playheadIndex + delta
                if next < 0 || next > last {
                    self.stop()
                    return
                }
                project.playheadIndex = next
            }
        }
    }
}
