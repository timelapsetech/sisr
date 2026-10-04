import SwiftUI

struct AppCommands: Commands {
    var body: some Commands {
        CommandGroup(replacing: .newItem) {
            Button("Open Sequence…") {
                NotificationCenter.default.post(name: .sisrOpenSequence, object: nil)
            }
            .keyboardShortcut("o", modifiers: .command)

            Button("Close Sequence") {
                NotificationCenter.default.post(name: .sisrCloseSequence, object: nil)
            }
            .keyboardShortcut("w", modifiers: [.command, .shift])
        }

        CommandMenu("Playback") {
            Button("Play/Pause") {
                NotificationCenter.default.post(name: .sisrTogglePlay, object: nil)
            }
            .keyboardShortcut(.space, modifiers: [])

            Button("Set In Point") {
                NotificationCenter.default.post(name: .sisrSetIn, object: nil)
            }
            .keyboardShortcut("i", modifiers: [])

            Button("Set Out Point") {
                NotificationCenter.default.post(name: .sisrSetOut, object: nil)
            }
            .keyboardShortcut("o", modifiers: [])

            Button("Clear In/Out") {
                NotificationCenter.default.post(name: .sisrClearInOut, object: nil)
            }
            .keyboardShortcut("x", modifiers: .option)

            Divider()

            Button("Step Backward") {
                NotificationCenter.default.post(name: .sisrStepBack, object: nil)
            }
            .keyboardShortcut(.leftArrow, modifiers: [])

            Button("Step Forward") {
                NotificationCenter.default.post(name: .sisrStepForward, object: nil)
            }
            .keyboardShortcut(.rightArrow, modifiers: [])
        }

        CommandMenu("Render") {
            Button("Render") {
                NotificationCenter.default.post(name: .sisrRender, object: nil)
            }
            .keyboardShortcut("r", modifiers: .command)
        }
    }
}

extension Notification.Name {
    static let sisrOpenSequence = Notification.Name("sisr.openSequence")
    /// Posted with a `URL` object to load a sequence folder (CLI / Finder / dock).
    static let sisrOpenDirectoryURL = Notification.Name("sisr.openDirectoryURL")
    static let sisrCloseSequence = Notification.Name("sisr.closeSequence")
    static let sisrTogglePlay = Notification.Name("sisr.togglePlay")
    static let sisrSetIn = Notification.Name("sisr.setIn")
    static let sisrSetOut = Notification.Name("sisr.setOut")
    static let sisrClearInOut = Notification.Name("sisr.clearInOut")
    static let sisrStepBack = Notification.Name("sisr.stepBack")
    static let sisrStepForward = Notification.Name("sisr.stepForward")
    static let sisrRender = Notification.Name("sisr.render")
    static let sisrToggleOriginal = Notification.Name("sisr.toggleOriginal")
}
