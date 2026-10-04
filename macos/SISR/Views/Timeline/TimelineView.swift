import SwiftUI
import SISRKit

struct TimelineView: View {
    @Bindable var project: SequenceProject
    var frameCache: FrameCache
    var playback: PlaybackController

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 10) {
                Button {
                    playback.toggle(project: project)
                } label: {
                    Image(systemName: playback.isPlaying ? "pause.fill" : "play.fill")
                        .font(.system(size: 13, weight: .semibold))
                        .frame(width: 28, height: 28)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.borderless)
                .disabled(!project.hasSequence)
                .help(playback.isPlaying ? "Pause (K)" : "Play (L / Space)")

                VStack(alignment: .leading, spacing: 1) {
                    Text(frameLabel)
                        .font(.system(.caption, design: .monospaced).weight(.medium))
                        .foregroundStyle(.primary)
                    if let date = project.dateString(at: project.playheadIndex) {
                        Text(DateOverlayFormatter.format(date, parts: project.render.dateParts))
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                            .lineLimit(1)
                    }
                }

                Spacer(minLength: 8)

                HStack(spacing: 6) {
                    MetricPill(
                        text: "In \(project.timeline.inIndex + 1)",
                        tone: Color.accentColor
                    )
                    MetricPill(
                        text: "Out \(project.timeline.outIndex + 1)",
                        tone: Color.accentColor
                    )
                }

                ControlGroup {
                    Button("I") { project.setInPoint() }
                        .help("Set In (I)")
                    Button("O") { project.setOutPoint() }
                        .help("Set Out (O)")
                }
                .controlSize(.small)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)

            FilmstripView(project: project, frameCache: frameCache)
                .frame(height: 76)
                .padding(.horizontal, 10)
                .padding(.bottom, 10)
        }
        .background(Theme.filmstripTrack)
        .overlay(alignment: .top) {
            SoftDivider()
        }
    }

    private var frameLabel: String {
        guard project.frameCount > 0 else { return "— / —" }
        let fps = max(0.01, project.render.fps)
        let t = Double(project.playheadIndex) / fps
        let tc = formatTimecode(t)
        return "\(project.playheadIndex + 1)/\(project.frameCount)  \(tc)"
    }

    private func formatTimecode(_ seconds: Double) -> String {
        let total = Int(seconds)
        let h = total / 3600
        let m = (total % 3600) / 60
        let s = total % 60
        let f = Int((seconds - Double(total)) * project.render.fps)
        if h > 0 {
            return String(format: "%02d:%02d:%02d:%02d", h, m, s, f)
        }
        return String(format: "%02d:%02d:%02d", m, s, f)
    }
}

struct FilmstripView: View {
    @Bindable var project: SequenceProject
    var frameCache: FrameCache

    var body: some View {
        GeometryReader { geo in
            let count = max(1, project.frameCount)
            let thumbWidth = max(36, geo.size.width / CGFloat(min(count, 40)))
            let visibleCount = Int(geo.size.width / thumbWidth) + 2

            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(Color.black.opacity(0.25))

                // In/out highlight
                if project.frameCount > 0 {
                    let range = project.timeline.clamped(to: project.frameCount)
                    let x0 = CGFloat(range.inIndex) / CGFloat(count) * geo.size.width
                    let x1 = CGFloat(range.outIndex + 1) / CGFloat(count) * geo.size.width
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(Color.accentColor.opacity(0.2))
                        .frame(width: max(2, x1 - x0))
                        .offset(x: x0)
                }

                ScrollView(.horizontal, showsIndicators: false) {
                    LazyHStack(spacing: 2) {
                        ForEach(0..<project.frameCount, id: \.self) { index in
                            FilmstripCell(
                                url: project.sequence?.frames[index].url,
                                selected: index == project.playheadIndex,
                                inRange: index >= project.timeline.inIndex
                                    && index <= project.timeline.outIndex,
                                frameCache: frameCache,
                                width: thumbWidth - 2
                            )
                            .frame(height: geo.size.height)
                        }
                    }
                }

                // Playhead
                if project.frameCount > 0 {
                    let x = (CGFloat(project.playheadIndex) + 0.5) / CGFloat(count) * geo.size.width
                    Capsule()
                        .fill(Color.accentColor)
                        .frame(width: 2, height: geo.size.height - 4)
                        .position(x: x, y: geo.size.height / 2)
                        .shadow(color: .black.opacity(0.35), radius: 2, y: 0)
                        .allowsHitTesting(false)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        guard project.frameCount > 0 else { return }
                        let t = GeometryUtil.clamp(value.location.x / geo.size.width, min: 0, max: 1)
                        project.playheadIndex = min(
                            project.frameCount - 1,
                            Int(t * CGFloat(project.frameCount))
                        )
                    }
            )
            .onChange(of: project.playheadIndex) { _, index in
                guard let urls = project.sequence?.frames.map(\.url) else { return }
                frameCache.prefetch(
                    urls: urls,
                    around: index,
                    window: max(4, visibleCount / 2),
                    maxPixelSize: 120
                )
            }
            .onAppear {
                guard let urls = project.sequence?.frames.map(\.url) else { return }
                frameCache.prefetch(
                    urls: urls,
                    around: project.playheadIndex,
                    window: max(4, visibleCount / 2),
                    maxPixelSize: 120
                )
            }
        }
    }
}

struct FilmstripCell: View {
    var url: URL?
    var selected: Bool
    var inRange: Bool
    var frameCache: FrameCache
    var width: CGFloat

    @State private var image: NSImage?

    var body: some View {
        ZStack {
            Color.black.opacity(0.35)
            if let image {
                Image(nsImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            }
        }
        .frame(width: width, height: 72)
        .clipped()
        .opacity(inRange ? 1 : 0.35)
        .overlay {
            if selected {
                RoundedRectangle(cornerRadius: 2, style: .continuous)
                    .strokeBorder(Color.accentColor, lineWidth: 2)
            }
        }
        .task(id: url?.path) {
            guard let url else { return }
            if let cached = frameCache.cachedThumbnail(for: url, maxPixelSize: 120) {
                image = cached
                return
            }
            image = await frameCache.thumbnail(for: url, maxPixelSize: 120)
        }
    }
}
