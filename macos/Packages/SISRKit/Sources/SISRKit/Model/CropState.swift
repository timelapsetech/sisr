import CoreGraphics
import Foundation

public enum CropAlign: String, Codable, Sendable, CaseIterable {
    case center
    case top
    case bottom
    case left
    case right
    case topLeft
    case topRight
    case bottomLeft
    case bottomRight
}

/// Normalized crop rect in source image coordinates (0…1), plus transform.
public struct CropState: Codable, Equatable, Sendable {
    /// Normalized rect in unit space of the oriented source image.
    public var normalizedRect: CGRect
    /// Straighten angle in degrees (−45…45).
    public var straightenDegrees: Double
    public var rotationQuarterTurns: Int
    public var flipHorizontal: Bool
    public var flipVertical: Bool
    public var aspectLock: AspectRatioLock

    public static let fullFrame = CropState(
        normalizedRect: CGRect(x: 0, y: 0, width: 1, height: 1),
        straightenDegrees: 0,
        rotationQuarterTurns: 0,
        flipHorizontal: false,
        flipVertical: false,
        aspectLock: .matchSource
    )

    public init(
        normalizedRect: CGRect = CGRect(x: 0, y: 0, width: 1, height: 1),
        straightenDegrees: Double = 0,
        rotationQuarterTurns: Int = 0,
        flipHorizontal: Bool = false,
        flipVertical: Bool = false,
        aspectLock: AspectRatioLock = .matchSource
    ) {
        self.normalizedRect = normalizedRect
        self.straightenDegrees = straightenDegrees
        self.rotationQuarterTurns = rotationQuarterTurns
        self.flipHorizontal = flipHorizontal
        self.flipVertical = flipVertical
        self.aspectLock = aspectLock
    }

    public func pixelRect(sourceSize: CGSize) -> CGRect {
        let r = normalizedRect
        var rect = CGRect(
            x: r.origin.x * sourceSize.width,
            y: r.origin.y * sourceSize.height,
            width: r.size.width * sourceSize.width,
            height: r.size.height * sourceSize.height
        )
        rect.size = GeometryUtil.evenSize(rect.size)
        rect.origin.x = rect.origin.x.rounded(.down)
        rect.origin.y = rect.origin.y.rounded(.down)
        return rect
    }

    public func pixelSize(sourceSize: CGSize) -> PixelSize {
        let r = pixelRect(sourceSize: sourceSize)
        return PixelSize(width: Int(r.width), height: Int(r.height)).even
    }

    public mutating func setAspectLock(_ lock: AspectRatioLock, sourceSize: CGSize) {
        aspectLock = lock
        applyAspectConstraint(sourceSize: sourceSize, align: .center, preferLargest: true)
    }

    public mutating func applyAspectConstraint(
        sourceSize: CGSize,
        align: CropAlign,
        preferLargest: Bool = false
    ) {
        let aspect: CGFloat
        switch aspectLock {
        case .free:
            return
        case .matchSource:
            guard sourceSize.height > 0 else { return }
            aspect = sourceSize.width / sourceSize.height
        default:
            guard let a = aspectLock.aspect else { return }
            aspect = a
        }

        let current = pixelRect(sourceSize: sourceSize)
        let largest = GeometryUtil.centeredAspectRect(in: sourceSize, aspect: aspect)
        var target: CGRect

        if preferLargest
            || current.width >= sourceSize.width * 0.98
            || current.height >= sourceSize.height * 0.98
        {
            target = largest
        } else {
            let currentAspect = current.width / max(current.height, 1)
            if abs(currentAspect - aspect) > 0.001 {
                var w = current.width
                var h = w / aspect
                if h > current.height {
                    h = current.height
                    w = h * aspect
                }
                if w > largest.width {
                    w = largest.width
                    h = largest.height
                }
                w = CGFloat(GeometryUtil.even(Int(w.rounded(.down))))
                h = CGFloat(GeometryUtil.even(Int(h.rounded(.down))))
                var x = current.midX - w / 2
                var y = current.midY - h / 2
                x = GeometryUtil.clamp(x, min: 0, max: sourceSize.width - w)
                y = GeometryUtil.clamp(y, min: 0, max: sourceSize.height - h)
                target = CGRect(x: x, y: y, width: w, height: h)
            } else {
                target = current
            }
        }

        target = alignRect(target, in: sourceSize, align: align)
        normalizedRect = CGRect(
            x: target.origin.x / sourceSize.width,
            y: target.origin.y / sourceSize.height,
            width: target.size.width / sourceSize.width,
            height: target.size.height / sourceSize.height
        )
    }

    public mutating func align(_ align: CropAlign, sourceSize: CGSize) {
        let current = pixelRect(sourceSize: sourceSize)
        let aligned = alignRect(current, in: sourceSize, align: align)
        normalizedRect = CGRect(
            x: aligned.origin.x / sourceSize.width,
            y: aligned.origin.y / sourceSize.height,
            width: aligned.size.width / sourceSize.width,
            height: aligned.size.height / sourceSize.height
        )
    }

    /// Scale crop around its center (zoom in = smaller crop).
    public mutating func zoom(factor: CGFloat, sourceSize: CGSize) {
        guard factor > 0 else { return }
        var rect = pixelRect(sourceSize: sourceSize)
        let cx = rect.midX
        let cy = rect.midY
        var w = rect.width / factor
        var h = rect.height / factor
        if let aspect = self.resolvedAspect(sourceSize: sourceSize) {
            h = w / aspect
        }
        w = max(2, CGFloat(GeometryUtil.even(Int(w.rounded(.down)))))
        h = max(2, CGFloat(GeometryUtil.even(Int(h.rounded(.down)))))
        w = min(w, sourceSize.width)
        h = min(h, sourceSize.height)
        var x = cx - w / 2
        var y = cy - h / 2
        x = GeometryUtil.clamp(x, min: 0, max: sourceSize.width - w)
        y = GeometryUtil.clamp(y, min: 0, max: sourceSize.height - h)
        rect = CGRect(x: x, y: y, width: w, height: h)
        normalizedRect = CGRect(
            x: rect.origin.x / sourceSize.width,
            y: rect.origin.y / sourceSize.height,
            width: rect.size.width / sourceSize.width,
            height: rect.size.height / sourceSize.height
        )
    }

    public mutating func rotateLeft() {
        rotationQuarterTurns = (rotationQuarterTurns + 3) % 4
    }

    public mutating func rotateRight() {
        rotationQuarterTurns = (rotationQuarterTurns + 1) % 4
    }

    /// Set crop from a rect in source-pixel (top-left) coordinates.
    public mutating func setPixelRect(_ rect: CGRect, sourceSize: CGSize, constrainAspect: Bool = true) {
        guard sourceSize.width > 0, sourceSize.height > 0 else { return }
        var r = rect.standardized
        r = r.intersection(CGRect(origin: .zero, size: sourceSize))
        guard r.width >= 2, r.height >= 2 else { return }

        if constrainAspect, let aspect = resolvedAspect(sourceSize: sourceSize) {
            // Fit the locked aspect inside the drawn rect, anchored to the drag start corner-ish center.
            var w = r.width
            var h = w / aspect
            if h > r.height {
                h = r.height
                w = h * aspect
            }
            w = max(2, CGFloat(GeometryUtil.even(Int(w.rounded(.down)))))
            h = max(2, CGFloat(GeometryUtil.even(Int(h.rounded(.down)))))
            let x = GeometryUtil.clamp(r.midX - w / 2, min: 0, max: sourceSize.width - w)
            let y = GeometryUtil.clamp(r.midY - h / 2, min: 0, max: sourceSize.height - h)
            r = CGRect(x: x, y: y, width: w, height: h)
        } else {
            r.size = GeometryUtil.evenSize(r.size)
            r.origin.x = GeometryUtil.clamp(r.origin.x.rounded(.down), min: 0, max: sourceSize.width - r.width)
            r.origin.y = GeometryUtil.clamp(r.origin.y.rounded(.down), min: 0, max: sourceSize.height - r.height)
        }

        normalizedRect = CGRect(
            x: r.origin.x / sourceSize.width,
            y: r.origin.y / sourceSize.height,
            width: r.size.width / sourceSize.width,
            height: r.size.height / sourceSize.height
        )
    }

    public enum Handle: Int, CaseIterable, Sendable {
        case topLeft, topRight, bottomLeft, bottomRight
        case top, bottom, left, right
    }

    /// Resize by dragging a handle; `fixed` corner/edge stays put when possible.
    public mutating func resize(
        handle: Handle,
        toPoint pointInSource: CGPoint,
        sourceSize: CGSize
    ) {
        var r = pixelRect(sourceSize: sourceSize)
        let minSize: CGFloat = 16
        var x0 = r.minX
        var y0 = r.minY
        var x1 = r.maxX
        var y1 = r.maxY
        let px = GeometryUtil.clamp(pointInSource.x, min: 0, max: sourceSize.width)
        let py = GeometryUtil.clamp(pointInSource.y, min: 0, max: sourceSize.height)

        switch handle {
        case .topLeft:
            x0 = min(px, x1 - minSize)
            y0 = min(py, y1 - minSize)
        case .topRight:
            x1 = max(px, x0 + minSize)
            y0 = min(py, y1 - minSize)
        case .bottomLeft:
            x0 = min(px, x1 - minSize)
            y1 = max(py, y0 + minSize)
        case .bottomRight:
            x1 = max(px, x0 + minSize)
            y1 = max(py, y0 + minSize)
        case .top:
            y0 = min(py, y1 - minSize)
        case .bottom:
            y1 = max(py, y0 + minSize)
        case .left:
            x0 = min(px, x1 - minSize)
        case .right:
            x1 = max(px, x0 + minSize)
        }

        var next = CGRect(x: x0, y: y0, width: x1 - x0, height: y1 - y0)

        if let aspect = resolvedAspect(sourceSize: sourceSize) {
            // Rebuild from the moving handle while locking aspect.
            switch handle {
            case .topLeft, .topRight, .bottomLeft, .bottomRight:
                var w = next.width
                var h = w / aspect
                if abs(next.height - h) > abs(next.width - next.height * aspect) {
                    h = next.height
                    w = h * aspect
                }
                switch handle {
                case .topLeft:
                    next = CGRect(x: x1 - w, y: y1 - h, width: w, height: h)
                case .topRight:
                    next = CGRect(x: x0, y: y1 - h, width: w, height: h)
                case .bottomLeft:
                    next = CGRect(x: x1 - w, y: y0, width: w, height: h)
                case .bottomRight:
                    next = CGRect(x: x0, y: y0, width: w, height: h)
                default:
                    break
                }
            case .top, .bottom:
                let h = next.height
                let w = h * aspect
                let x = r.midX - w / 2
                if handle == .top {
                    next = CGRect(x: x, y: y1 - h, width: w, height: h)
                } else {
                    next = CGRect(x: x, y: y0, width: w, height: h)
                }
            case .left, .right:
                let w = next.width
                let h = w / aspect
                let y = r.midY - h / 2
                if handle == .left {
                    next = CGRect(x: x1 - w, y: y, width: w, height: h)
                } else {
                    next = CGRect(x: x0, y: y, width: w, height: h)
                }
            }
        }

        // Clamp into source bounds without changing size when possible.
        next.size.width = max(minSize, min(next.width, sourceSize.width))
        next.size.height = max(minSize, min(next.height, sourceSize.height))
        next.origin.x = GeometryUtil.clamp(next.origin.x, min: 0, max: sourceSize.width - next.width)
        next.origin.y = GeometryUtil.clamp(next.origin.y, min: 0, max: sourceSize.height - next.height)
        setPixelRect(next, sourceSize: sourceSize, constrainAspect: false)
    }

    public func resolvedAspect(sourceSize: CGSize) -> CGFloat? {
        switch aspectLock {
        case .free: return nil
        case .matchSource:
            guard sourceSize.height > 0 else { return nil }
            return sourceSize.width / sourceSize.height
        default:
            return aspectLock.aspect
        }
    }

    private func alignRect(_ rect: CGRect, in bounds: CGSize, align: CropAlign) -> CGRect {
        var r = rect
        switch align {
        case .center:
            r.origin.x = ((bounds.width - r.width) / 2).rounded(.down)
            r.origin.y = ((bounds.height - r.height) / 2).rounded(.down)
        case .top:
            r.origin.y = 0
            r.origin.x = ((bounds.width - r.width) / 2).rounded(.down)
        case .bottom:
            r.origin.y = (bounds.height - r.height).rounded(.down)
            r.origin.x = ((bounds.width - r.width) / 2).rounded(.down)
        case .left:
            r.origin.x = 0
            r.origin.y = ((bounds.height - r.height) / 2).rounded(.down)
        case .right:
            r.origin.x = (bounds.width - r.width).rounded(.down)
            r.origin.y = ((bounds.height - r.height) / 2).rounded(.down)
        case .topLeft:
            r.origin = .zero
        case .topRight:
            r.origin.x = (bounds.width - r.width).rounded(.down)
            r.origin.y = 0
        case .bottomLeft:
            r.origin.x = 0
            r.origin.y = (bounds.height - r.height).rounded(.down)
        case .bottomRight:
            r.origin.x = (bounds.width - r.width).rounded(.down)
            r.origin.y = (bounds.height - r.height).rounded(.down)
        }
        r.origin.x = GeometryUtil.clamp(r.origin.x, min: 0, max: max(0, bounds.width - r.width))
        r.origin.y = GeometryUtil.clamp(r.origin.y, min: 0, max: max(0, bounds.height - r.height))
        return r
    }
}
