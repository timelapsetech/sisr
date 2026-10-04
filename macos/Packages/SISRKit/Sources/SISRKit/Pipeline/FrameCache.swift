import AppKit
import Foundation
import ImageIO

public final class FrameCache: @unchecked Sendable {
    private let cache = NSCache<NSString, NSImage>()
    /// All ImageIO work runs here at user-initiated QoS so UI never waits on a Utility thread.
    private let decodeQueue = DispatchQueue(
        label: "com.sisr.framecache.decode",
        qos: .userInitiated,
        attributes: .concurrent
    )
    private var prefetchTask: Task<Void, Never>?
    /// When true, skip new decodes/prefetch so render can claim ImageIO / IOSurface budget.
    public var isPaused = false

    public init(countLimit: Int = 64) {
        cache.countLimit = countLimit
    }

    public func clear() {
        cache.removeAllObjects()
        prefetchTask?.cancel()
        prefetchTask = nil
    }

    public func pauseForRender() {
        isPaused = true
        prefetchTask?.cancel()
        prefetchTask = nil
        cache.removeAllObjects()
    }

    public func resumeAfterRender() {
        isPaused = false
    }

    /// Non-blocking cache lookup for synchronous view bodies.
    public func cachedThumbnail(for url: URL, maxPixelSize: CGFloat) -> NSImage? {
        cache.object(forKey: cacheKey(url: url, size: maxPixelSize) as NSString)
    }

    /// Decode (or return cached) thumbnail off the main thread.
    public func thumbnail(for url: URL, maxPixelSize: CGFloat) async -> NSImage? {
        let key = cacheKey(url: url, size: maxPixelSize)
        if let hit = cache.object(forKey: key as NSString) {
            return hit
        }
        if isPaused { return nil }

        return await withCheckedContinuation { continuation in
            decodeQueue.async {
                if self.isPaused {
                    continuation.resume(returning: nil)
                    return
                }
                if let hit = self.cache.object(forKey: key as NSString) {
                    continuation.resume(returning: hit)
                    return
                }
                let image = self.decodeThumbnail(url: url, maxPixelSize: maxPixelSize)
                if let image {
                    self.cache.setObject(image, forKey: key as NSString)
                }
                continuation.resume(returning: image)
            }
        }
    }

    public func prefetch(urls: [URL], around index: Int, window: Int, maxPixelSize: CGFloat) {
        guard !isPaused else { return }
        prefetchTask?.cancel()
        let start = max(0, index - window)
        let end = min(urls.count, index + window + 1)
        guard start < end else { return }
        let slice = Array(urls[start..<end])

        // Match decode-queue QoS — never Utility, which caused priority inversions when
        // the main thread touched ImageIO while prefetch held lower-priority work.
        prefetchTask = Task(priority: .userInitiated) { [weak self] in
            guard let self, !self.isPaused else { return }
            await withTaskGroup(of: Void.self) { group in
                for url in slice {
                    group.addTask {
                        if Task.isCancelled || self.isPaused { return }
                        _ = await self.thumbnail(for: url, maxPixelSize: maxPixelSize)
                    }
                }
            }
        }
    }

    private func cacheKey(url: URL, size: CGFloat) -> String {
        "\(url.path)#\(Int(size))"
    }

    private func decodeThumbnail(url: URL, maxPixelSize: CGFloat) -> NSImage? {
        guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else { return nil }
        let options: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceThumbnailMaxPixelSize: max(64, Int(maxPixelSize)),
            kCGImageSourceCreateThumbnailWithTransform: true,
            // Avoid the shared ImageIO cache lock path that amplified QoS inversions.
            kCGImageSourceShouldCacheImmediately: false,
        ]
        guard let cg = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else {
            return nil
        }
        return NSImage(cgImage: cg, size: NSSize(width: cg.width, height: cg.height))
    }
}
