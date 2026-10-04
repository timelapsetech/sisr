import CoreGraphics
import Foundation
import Testing
@testable import SISRKit

@Suite("Models")
struct ModelTests {
    @Test func evenDimensions() {
        #expect(GeometryUtil.even(1921) == 1920)
        #expect(GeometryUtil.even(1080) == 1080)
    }

    @Test func outputNaming() {
        var settings = RenderSettings(preset: .p1080, codec: .prores, overlay: .date, outputBaseName: "clip")
        let name = OutputNaming.makeFilename(
            baseName: "clip",
            settings: settings,
            cropLabel: "p1080",
            outputSize: PixelSize(width: 1920, height: 1080)
        )
        #expect(name == "clip_p1080_date_prores.mov")

        settings.codec = .h264
        settings.overlay = .none
        let name2 = OutputNaming.makeFilename(
            baseName: "clip",
            settings: settings,
            cropLabel: nil,
            outputSize: nil
        )
        #expect(name2.hasSuffix(".mp4"))
    }

    @Test func resolutionCheckNative() {
        let crop = PixelSize(width: 4000, height: 2250)
        let check = ResolutionCheck.evaluate(crop: crop, preset: .p1080)
        #expect(check?.fitness == .native)
    }

    @Test func resolutionCheckUpscaled() {
        let crop = PixelSize(width: 1600, height: 900)
        let check = ResolutionCheck.evaluate(crop: crop, preset: .p1080)
        #expect(check?.fitness == .upscaled)
        #expect(check?.willUpscale == true)
    }

    @Test func heavyUpscaleStillAllowed() {
        let crop = PixelSize(width: 640, height: 360)
        let check = ResolutionCheck.evaluate(crop: crop, preset: .uhd8k)
        #expect(check?.fitness == .tooSmall)
        #expect(check?.willUpscale == true)
        #expect(check?.badgeLabel.contains("Heavy upscale") == true)
    }

    @Test func cropAspectLock() {
        var crop = CropState.fullFrame
        let size = CGSize(width: 6000, height: 4000)
        crop.setAspectLock(.ratio16x9, sourceSize: size)
        let px = crop.pixelSize(sourceSize: size)
        let aspect = Double(px.width) / Double(px.height)
        #expect(abs(aspect - 16.0 / 9.0) < 0.02)
        #expect(px.width % 2 == 0)
        #expect(px.height % 2 == 0)
    }

    @Test func renderSettingsOutputSize() {
        let settings = RenderSettings(preset: .uhd4k)
        let out = settings.outputPixelSize(cropSize: PixelSize(width: 5000, height: 3000))
        #expect(out.width == 3840)
        #expect(out.height == 2160)
    }

    @Test func h264BitrateLadder() {
        #expect(VideoBitrate.h264BitsPerSecond(width: 1920, height: 1080) == 10_000_000)
        #expect(VideoBitrate.h264BitsPerSecond(width: 1080, height: 1920) == 10_000_000)
        #expect(VideoBitrate.h264BitsPerSecond(width: 3840, height: 2160) == 15_000_000)
        #expect(VideoBitrate.h264BitsPerSecond(width: 1280, height: 720) == 5_000_000)
        #expect(VideoBitrate.hevcBitsPerSecond(width: 1920, height: 1080) < 10_000_000)
    }

    @Test func videoEncodeOverrides() {
        var encode = VideoEncodeSettings.automatic
        #expect(encode.usesAutomaticDefaults)
        #expect(
            encode.resolvedAverageMbps(codec: .h264, width: 1920, height: 1080) == 10
        )
        encode.averageBitRateMbps = 20
        encode.maxBitRateMbps = 30
        encode.quality = 0.9
        #expect(!encode.usesAutomaticDefaults)
        #expect(encode.resolvedAverageBitsPerSecond(codec: .h264, width: 1920, height: 1080) == 20_000_000)
        #expect(encode.resolvedMaxBitsPerSecond(codec: .h264, width: 1920, height: 1080) == 30_000_000)
        #expect(encode.resolvedQuality == 0.9)
        encode.resetToDefaults()
        #expect(encode.usesAutomaticDefaults)
    }

    @Test func straightenCoverScaleCenterNeedsNoZoom() {
        let source = CGSize(width: 1000, height: 1000)
        let crop = CGRect(x: 300, y: 300, width: 400, height: 400)
        let scale = StraightenGeometry.coverScale(sourceSize: source, cropRect: crop, degrees: 5)
        #expect(abs(scale - 1) < 0.001)
    }

    @Test func straightenCoverScaleNearEdgeZooms() {
        let source = CGSize(width: 1000, height: 1000)
        let crop = CGRect(x: 0, y: 0, width: 400, height: 400)
        let scale = StraightenGeometry.coverScale(sourceSize: source, cropRect: crop, degrees: 15)
        #expect(scale > 1.01)
    }
}
