import AppKit
import CoreGraphics
import CoreImage
import Foundation

public enum OverlayRenderer {
    public static func drawOverlay(
        on image: CIImage,
        overlay: OverlayType,
        text: String,
        outputSize: PixelSize,
        numberWidth _: Int
    ) -> CIImage {
        guard overlay != .none, !text.isEmpty || overlay == .frame else { return image }

        let width = outputSize.width
        let height = outputSize.height
        guard width > 0, height > 0 else { return image }

        let displayText: String
        switch overlay {
        case .none:
            return image
        case .date:
            displayText = text
        case .frame:
            displayText = text
        }

        let fontSize = DateOverlayFormatter.overlayFontSize(
            for: displayText,
            frameWidth: width,
            frameHeight: height
        )
        let boxPadding = CGFloat(fontSize) * 0.25

        let rep = NSBitmapImageRep(
            bitmapDataPlanes: nil,
            pixelsWide: width,
            pixelsHigh: height,
            bitsPerSample: 8,
            samplesPerPixel: 4,
            hasAlpha: true,
            isPlanar: false,
            colorSpaceName: .deviceRGB,
            bytesPerRow: 0,
            bitsPerPixel: 0
        )
        guard let rep else { return image }
        // Match point size to pixel size so 1pt == 1px when drawing overlays.
        rep.size = NSSize(width: width, height: height)

        NSGraphicsContext.saveGraphicsState()
        guard let ctx = NSGraphicsContext(bitmapImageRep: rep) else {
            NSGraphicsContext.restoreGraphicsState()
            return image
        }
        NSGraphicsContext.current = ctx

        let font = NSFont(name: "SFMono-Regular", size: CGFloat(fontSize))
            ?? NSFont.monospacedSystemFont(ofSize: CGFloat(fontSize), weight: .regular)

        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor.white,
        ]
        let nsText = NSAttributedString(string: displayText, attributes: attrs)
        let textSize = nsText.size()
        let boxSize = CGSize(
            width: textSize.width + boxPadding * 2,
            height: textSize.height + boxPadding * 2
        )

        let marginX = CGFloat(width) * 0.05
        let marginY = CGFloat(height) * 0.05

        let boxOrigin: CGPoint
        switch overlay {
        case .date:
            boxOrigin = CGPoint(
                x: CGFloat(width) - boxSize.width - marginX,
                y: marginY
            )
        case .frame:
            boxOrigin = CGPoint(
                x: (CGFloat(width) - boxSize.width) / 2,
                y: CGFloat(height) - boxSize.height - marginY
            )
        case .none:
            boxOrigin = .zero
        }

        let boxRect = CGRect(origin: boxOrigin, size: boxSize)
        NSColor.black.withAlphaComponent(0.5).setFill()
        boxRect.fill()

        let textOrigin = CGPoint(
            x: boxRect.minX + boxPadding,
            y: boxRect.minY + boxPadding
        )
        nsText.draw(at: textOrigin)

        NSGraphicsContext.restoreGraphicsState()

        guard let cgImage = rep.cgImage else { return image }
        let overlayCI = CIImage(cgImage: cgImage)
        return overlayCI.composited(over: image)
    }

    public static func frameOverlayText(
        indexInRender: Int,
        sourceFrameNumber: Int,
        mode: FrameNumberMode,
        pad: Int,
        totalFrames: Int
    ) -> String {
        let value: Int
        switch mode {
        case .countFromInPoint:
            value = indexInRender + 1
        case .useSourceNumbers:
            value = sourceFrameNumber
        }
        let width = max(1, pad, String(totalFrames).count)
        return String(format: "FRAME %0\(width)d", value)
    }
}
