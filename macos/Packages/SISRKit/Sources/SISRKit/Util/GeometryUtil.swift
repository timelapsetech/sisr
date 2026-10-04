import CoreGraphics
import Foundation

public enum GeometryUtil {
    /// Round down to the nearest even integer (codec-friendly).
    public static func even(_ value: Int) -> Int {
        value - (value % 2)
    }

    public static func evenSize(_ size: CGSize) -> CGSize {
        CGSize(
            width: CGFloat(even(Int(size.width.rounded(.down)))),
            height: CGFloat(even(Int(size.height.rounded(.down))))
        )
    }

    public static func clamp(_ value: CGFloat, min minValue: CGFloat, max maxValue: CGFloat) -> CGFloat {
        Swift.max(minValue, Swift.min(maxValue, value))
    }

    /// Fit `inner` inside `outer` while preserving aspect ratio.
    public static func aspectFit(_ inner: CGSize, in outer: CGSize) -> CGSize {
        guard inner.width > 0, inner.height > 0, outer.width > 0, outer.height > 0 else {
            return .zero
        }
        let scale = min(outer.width / inner.width, outer.height / inner.height)
        return evenSize(CGSize(width: inner.width * scale, height: inner.height * scale))
    }

    /// Largest even rect of `aspect` centered in `bounds`.
    public static func centeredAspectRect(in bounds: CGSize, aspect: CGFloat) -> CGRect {
        guard bounds.width > 0, bounds.height > 0, aspect > 0 else { return .zero }
        let boundsAspect = bounds.width / bounds.height
        let width: CGFloat
        let height: CGFloat
        if boundsAspect > aspect {
            height = bounds.height
            width = height * aspect
        } else {
            width = bounds.width
            height = width / aspect
        }
        let evenW = CGFloat(even(Int(width.rounded(.down))))
        let evenH = CGFloat(even(Int(height.rounded(.down))))
        let x = ((bounds.width - evenW) / 2).rounded(.down)
        let y = ((bounds.height - evenH) / 2).rounded(.down)
        return CGRect(x: x, y: y, width: evenW, height: evenH)
    }
}
