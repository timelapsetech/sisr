import AppKit
import SwiftUI
import SISRKit

struct ViewerView: View {
    @Bindable var project: SequenceProject
    var frameCache: FrameCache
    var playback: PlaybackController

    @State private var compositionImage: NSImage?
    @State private var debounce: Task<Void, Never>?

    private let contentInset: CGFloat = 12

    var body: some View {
        GeometryReader { geo in
            ZStack {
                Theme.viewerCanvas

                if project.hasSequence {
                    GeometryReader { inner in
                        let fitted = CropOverlayView.fittedImageRect(
                            sourceSize: project.sourceSize,
                            in: inner.size
                        )
                        let cropNorm = project.crop.normalizedRect
                        let coverScale = straightenCoverScale
                        let anchor = UnitPoint(x: cropNorm.midX, y: cropNorm.midY)

                        ZStack {
                            if let compositionImage {
                                Image(nsImage: compositionImage)
                                    .resizable()
                                    .interpolation(.high)
                                    .frame(width: fitted.width, height: fitted.height)
                                    // Image rotates/zooms under a fixed crop overlay.
                                    .rotationEffect(
                                        .degrees(-project.crop.straightenDegrees),
                                        anchor: anchor
                                    )
                                    .scaleEffect(coverScale, anchor: anchor)
                                    .frame(width: fitted.width, height: fitted.height)
                                    .clipped()
                                    .position(x: fitted.midX, y: fitted.midY)
                            } else {
                                ProgressView()
                                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                            }

                            // Crop box stays screen-aligned; outside remains visible (dimmed).
                            if !project.showOriginal {
                                CropOverlayView(project: project)
                            }
                        }
                    }
                    .padding(contentInset)
                } else {
                    EmptyStateView {
                        NotificationCenter.default.post(name: .sisrOpenSequence, object: nil)
                    }
                }
            }
            .frame(width: geo.size.width, height: geo.size.height)
            .focusable()
            .onKeyPress(keys: [.init("j"), .init("J")]) { _ in
                playback.shuttle(project: project, direction: -1)
                return .handled
            }
            .onKeyPress(keys: [.init("k"), .init("K")]) { _ in
                playback.shuttle(project: project, direction: 0)
                return .handled
            }
            .onKeyPress(keys: [.init("l"), .init("L")]) { _ in
                playback.shuttle(project: project, direction: 1)
                return .handled
            }
            .onKeyPress(keys: [.init("\\")]) { _ in
                project.showOriginal.toggle()
                return .handled
            }
            .onChange(of: project.playheadIndex) { _, _ in refreshPreview(in: geo.size) }
            .onChange(of: project.crop.flipHorizontal) { _, _ in refreshPreview(in: geo.size) }
            .onChange(of: project.crop.flipVertical) { _, _ in refreshPreview(in: geo.size) }
            .onChange(of: project.crop.rotationQuarterTurns) { _, _ in refreshPreview(in: geo.size) }
            .onChange(of: project.adjustments) { _, _ in refreshPreview(in: geo.size) }
            .onChange(of: project.showOriginal) { _, _ in refreshPreview(in: geo.size) }
            .onChange(of: project.sequence?.directory.path) { _, _ in refreshPreview(in: geo.size) }
            .onAppear { refreshPreview(in: geo.size) }
        }
    }

    /// Zoom only when the crop is near an edge and rotation would sample outside the image.
    private var straightenCoverScale: CGFloat {
        guard project.sourceSize.width > 0 else { return 1 }
        let pixel = project.crop.pixelRect(sourceSize: project.sourceSize)
        return StraightenGeometry.coverScale(
            sourceSize: project.sourceSize,
            cropRect: pixel,
            degrees: project.crop.straightenDegrees
        )
    }

    private func refreshPreview(in size: CGSize) {
        debounce?.cancel()
        debounce = Task {
            try? await Task.sleep(nanoseconds: 16_000_000)
            guard !Task.isCancelled else { return }
            await updateImage(viewSize: size)
        }
    }

    @MainActor
    private func updateImage(viewSize: CGSize) async {
        guard let sequence = project.sequence,
              sequence.frames.indices.contains(project.playheadIndex)
        else {
            compositionImage = nil
            return
        }

        let frame = sequence.frames[project.playheadIndex]
        let maxPixel = max(viewSize.width, viewSize.height) * 2

        if compositionImage == nil {
            if let cached = frameCache.cachedThumbnail(for: frame.url, maxPixelSize: maxPixel) {
                compositionImage = cached
            } else {
                compositionImage = await frameCache.thumbnail(for: frame.url, maxPixelSize: maxPixel)
            }
        }

        let urls = sequence.frames.map(\.url)
        frameCache.prefetch(urls: urls, around: project.playheadIndex, window: 8, maxPixelSize: maxPixel)

        // Full-frame graded image; straighten is applied live in the view.
        let input = FramePipelineInput(
            imageURL: frame.url,
            crop: project.crop,
            adjustments: project.showOriginal ? .identity : project.adjustments,
            outputSize: project.outputPixelSize,
            overlay: .none,
            overlayText: "",
            showOriginal: project.showOriginal,
            compositionPreview: !project.showOriginal,
            exposureBias: 0
        )

        let image: NSImage? = await Task.detached(priority: .userInitiated) {
            guard let cg = FramePipeline().renderCGImage(from: input) else { return nil }
            return NSImage(cgImage: cg, size: NSSize(width: cg.width, height: cg.height))
        }.value

        if let image {
            compositionImage = image
        }
    }
}

struct EmptyStateView: View {
    var onOpen: () -> Void

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "square.stack.3d.up")
                .font(.system(size: 44, weight: .ultraLight))
                .symbolRenderingMode(.hierarchical)
                .foregroundStyle(.secondary)
            VStack(spacing: 6) {
                Text("Open an image sequence")
                    .font(.title2.weight(.semibold))
                Text("Drop a folder of numbered frames — img_0001.jpg, img_0002.jpg… — or choose Open.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .font(.callout)
                    .frame(maxWidth: 360)
            }
            Button("Open Sequence…", action: onOpen)
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .keyboardShortcut("o", modifiers: .command)
        }
        .padding(36)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(.ultraThinMaterial.opacity(0.35))
        )
        .overlay {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [7, 5]))
                .foregroundStyle(.white.opacity(0.18))
        }
        .frame(maxWidth: 460)
    }
}
