import AppKit
import Foundation

/// Public documentation URLs used in Help / Settings (App Store support & privacy).
enum SiteLinks {
    static let home = URL(string: "https://timelapsetech.github.io/sisr/")!
    static let macGuide = URL(string: "https://timelapsetech.github.io/sisr/macos-guide.html")!
    static let privacy = URL(string: "https://timelapsetech.github.io/sisr/privacy.html")!
    static let support = URL(string: "https://timelapsetech.github.io/sisr/support.html")!

    static func open(_ url: URL) {
        NSWorkspace.shared.open(url)
    }
}
