import SwiftUI
import SISRKit

struct InspectorView: View {
    @Bindable var project: SequenceProject

    var body: some View {
        Form {
            CropSection(project: project)
            TransformSection(project: project)
            ColorSection(project: project)
            DetailSection(project: project)
            DeflickerSection(project: project)
        }
        .formStyle(.grouped)
        .background(.regularMaterial)
    }
}

// MARK: - Crop & Frame

struct CropSection: View {
    @Bindable var project: SequenceProject
    @AppStorage("sisr.ui.cropAlign") private var showAlign = false
    @AppStorage("sisr.ui.cropFitness") private var showFitness = false

    private let quickPresets: [OutputPreset] = [
        .uhd8k, .uhd4k, .p1080, .p720, .p360, .instagramStory, .square,
    ]

    var body: some View {
        Section {
            Picker("Aspect", selection: Binding(
                get: { project.crop.aspectLock },
                set: { project.crop.setAspectLock($0, sourceSize: project.sourceSize) }
            )) {
                ForEach(AspectRatioLock.allCases) { lock in
                    Text(lock.displayName).tag(lock)
                }
            }
            .disabled(project.render.preset.locksAspect)

            VStack(alignment: .leading, spacing: 8) {
                Text("Quick sizes")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(quickPresets, id: \.self) { preset in
                            let selected = project.render.preset == preset
                            Button {
                                project.applyPreset(preset)
                            } label: {
                                Text(preset.displayName)
                                    .font(.caption.weight(.medium))
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 5)
                                    .background(
                                        selected ? Color.accentColor.opacity(0.22) : Color.primary.opacity(0.06),
                                        in: Capsule(style: .continuous)
                                    )
                                    .overlay {
                                        Capsule(style: .continuous)
                                            .strokeBorder(
                                                selected ? Color.accentColor.opacity(0.55) : Color.clear,
                                                lineWidth: 1
                                            )
                                    }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }

            LabeledContent("Crop pixels") {
                Text(project.cropPixelSize.label)
                    .font(.system(.body, design: .monospaced))
                    .foregroundStyle(.secondary)
            }

            if let current = project.currentOutputResolutionCheck, current.willUpscale {
                UpscaleWarningBanner(text: current.warningSummary, fitness: current.fitness)
            }

            DisclosureGroup(isExpanded: $showAlign) {
                AdjustmentSliderRow(
                    title: "Zoom",
                    value: Binding(get: { zoomValue }, set: { setZoom($0) }),
                    range: 1...4,
                    resetValue: 1,
                    format: .number.precision(.fractionLength(2)),
                    unit: "×"
                )

                VStack(alignment: .leading, spacing: 8) {
                    Text("Align")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    HStack(spacing: 6) {
                        alignButton("Top", systemImage: "rectangle.tophalf.filled", .top)
                        alignButton("Center", systemImage: "rectangle.center.inset.filled", .center)
                        alignButton("Bottom", systemImage: "rectangle.bottomhalf.filled", .bottom)
                    }
                    HStack(spacing: 6) {
                        alignButton("Left", systemImage: "rectangle.lefthalf.filled", .left)
                        alignButton("Right", systemImage: "rectangle.righthalf.filled", .right)
                        Spacer(minLength: 0)
                    }
                }
                .padding(.top, 4)
            } label: {
                DisclosureLabel(title: "Align & zoom", subtitle: showAlign ? nil : "Zoom and edge alignment")
            }

            if !project.resolutionChecks.isEmpty {
                DisclosureGroup(isExpanded: $showFitness) {
                    ForEach(project.resolutionChecks) { check in
                        Button {
                            project.applyPreset(check.preset)
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: project.render.preset == check.preset
                                      ? "checkmark.circle.fill" : "circle")
                                    .foregroundStyle(project.render.preset == check.preset
                                                     ? AnyShapeStyle(Color.accentColor)
                                                     : AnyShapeStyle(.tertiary))
                                    .imageScale(.small)
                                Text(check.preset.displayName)
                                    .foregroundStyle(.primary)
                                Spacer(minLength: 4)
                                Text(check.target.label)
                                    .font(.system(.caption2, design: .monospaced))
                                    .foregroundStyle(.secondary)
                                FitnessBadge(label: check.badgeLabel, fitness: check.fitness)
                            }
                            .padding(.vertical, 4)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                } label: {
                    DisclosureLabel(
                        title: "Resolution fitness",
                        subtitle: showFitness ? nil : "Compare output sizes vs crop"
                    )
                }
            }
        } header: {
            PanelSectionHeader(title: "Crop & Frame", systemImage: "crop")
        } footer: {
            Text("Drag on the viewer to draw a crop. Outside the box stays visible but dimmed.")
        }
    }

    private var zoomValue: Double {
        let full = project.sourceSize.width * project.sourceSize.height
        let crop = CGFloat(project.cropPixelSize.width * project.cropPixelSize.height)
        guard crop > 0 else { return 1 }
        return Double(sqrt(full / crop))
    }

    private func setZoom(_ value: Double) {
        var crop = project.crop
        if let lock = project.render.preset.aspectLock {
            crop.aspectLock = lock
        }
        crop.normalizedRect = CGRect(x: 0, y: 0, width: 1, height: 1)
        crop.applyAspectConstraint(sourceSize: project.sourceSize, align: .center)
        crop.zoom(factor: CGFloat(value), sourceSize: project.sourceSize)
        project.crop = crop
    }

    private func alignButton(_ title: String, systemImage: String, _ align: CropAlign) -> some View {
        Button {
            project.crop.align(align, sourceSize: project.sourceSize)
        } label: {
            Label(title, systemImage: systemImage)
                .labelStyle(.titleAndIcon)
                .frame(maxWidth: .infinity)
        }
        .controlSize(.small)
        .buttonStyle(.bordered)
    }
}

// MARK: - Transform

struct TransformSection: View {
    @Bindable var project: SequenceProject
    @AppStorage("sisr.ui.transformMore") private var showMore = false

    var body: some View {
        Section {
            AdjustmentSliderRow(
                title: "Straighten",
                value: $project.crop.straightenDegrees,
                range: -45...45,
                resetValue: 0,
                format: .number.precision(.fractionLength(1)),
                unit: "°",
                fieldWidth: 52
            )

            HStack(spacing: 8) {
                Button {
                    project.crop.rotateLeft()
                } label: {
                    Label("Left", systemImage: "rotate.left")
                        .frame(maxWidth: .infinity)
                }
                Button {
                    project.crop.rotateRight()
                } label: {
                    Label("Right", systemImage: "rotate.right")
                        .frame(maxWidth: .infinity)
                }
            }
            .controlSize(.small)
            .buttonStyle(.bordered)

            DisclosureGroup(isExpanded: $showMore) {
                Toggle(isOn: $project.crop.flipHorizontal) {
                    Label("Flip Horizontal", systemImage: "arrow.left.and.right.righttriangle.left.righttriangle.right")
                }
                Toggle(isOn: $project.crop.flipVertical) {
                    Label("Flip Vertical", systemImage: "arrow.up.and.down.righttriangle.up.righttriangle.down")
                }
                Button("Reset Transform") {
                    project.crop.straightenDegrees = 0
                    project.crop.rotationQuarterTurns = 0
                    project.crop.flipHorizontal = false
                    project.crop.flipVertical = false
                }
                .controlSize(.small)
            } label: {
                DisclosureLabel(
                    title: "Flips & reset",
                    subtitle: showMore ? nil : flipSummary
                )
            }
        } header: {
            PanelSectionHeader(title: "Transform", systemImage: "rotate.right")
        } footer: {
            Text("Type a degree value or drag the slider. Double-click the slider to zero.")
        }
        .onAppear {
            if project.crop.flipHorizontal || project.crop.flipVertical {
                showMore = true
            }
        }
    }

    private var flipSummary: String {
        var parts: [String] = []
        if project.crop.flipHorizontal { parts.append("H") }
        if project.crop.flipVertical { parts.append("V") }
        if project.crop.rotationQuarterTurns != 0 {
            parts.append("\(project.crop.rotationQuarterTurns * 90)°")
        }
        return parts.isEmpty ? "Mirror and clear transform" : "Active: \(parts.joined(separator: " · "))"
    }
}

// MARK: - Color

struct ColorSection: View {
    @Bindable var project: SequenceProject
    @AppStorage("sisr.ui.colorControls") private var showColor = false

    var body: some View {
        Section {
            DisclosureGroup(isExpanded: $showColor) {
                AdjustmentSliderRow(title: "Exposure", value: $project.adjustments.color.exposure, range: -2...2)
                AdjustmentSliderRow(title: "Contrast", value: $project.adjustments.color.contrast, range: -1...1)
                AdjustmentSliderRow(title: "Highlights", value: $project.adjustments.color.highlights, range: -1...1)
                AdjustmentSliderRow(title: "Shadows", value: $project.adjustments.color.shadows, range: -1...1)
                AdjustmentSliderRow(title: "Saturation", value: $project.adjustments.color.saturation, range: -1...1)
                AdjustmentSliderRow(title: "Vibrance", value: $project.adjustments.color.vibrance, range: -1...1)
                AdjustmentSliderRow(title: "Temperature", value: $project.adjustments.color.temperature, range: -1...1)
                AdjustmentSliderRow(title: "Tint", value: $project.adjustments.color.tint, range: -1...1)

                HStack(spacing: 8) {
                    Button("Auto") {
                        project.adjustments.color.shadows = 0.15
                        project.adjustments.color.contrast = 0.08
                        project.adjustments.color.vibrance = 0.1
                        showColor = true
                    }
                    .controlSize(.small)
                    Spacer()
                    Button("Reset", role: .destructive) {
                        project.adjustments.color = .identity
                    }
                    .controlSize(.small)
                }
            } label: {
                DisclosureLabel(
                    title: "Color adjustments",
                    subtitle: showColor ? nil : colorSummary
                )
            }
        } header: {
            PanelSectionHeader(title: "Color", systemImage: "slider.horizontal.3")
        } footer: {
            if showColor {
                Text("Each row accepts typed values. Double-click a slider to reset it.")
            }
        }
        .onAppear {
            if !project.adjustments.color.isIdentity { showColor = true }
        }
        .onChange(of: project.adjustments.color) { _, color in
            if !color.isIdentity { showColor = true }
        }
    }

    private var colorSummary: String {
        project.adjustments.color.isIdentity
            ? "Exposure, contrast, white balance…"
            : "Adjustments active"
    }
}

// MARK: - Detail

struct DetailSection: View {
    @Bindable var project: SequenceProject
    @AppStorage("sisr.ui.detail") private var showDetail = false

    var body: some View {
        Section {
            DisclosureGroup(isExpanded: $showDetail) {
                AdjustmentSliderRow(
                    title: "Sharpen",
                    value: $project.adjustments.detail.sharpen,
                    range: 0...1,
                    resetValue: 0
                )
                AdjustmentSliderRow(
                    title: "Noise Reduction",
                    value: $project.adjustments.detail.noiseReduction,
                    range: 0...1,
                    resetValue: 0
                )
                AdjustmentSliderRow(
                    title: "Vignette",
                    value: $project.adjustments.detail.vignette,
                    range: 0...1,
                    resetValue: 0
                )
                Button("Reset Detail") {
                    project.adjustments.detail = .identity
                }
                .controlSize(.small)
            } label: {
                DisclosureLabel(
                    title: "Sharpen, noise, vignette",
                    subtitle: showDetail ? nil : detailSummary
                )
            }
        } header: {
            PanelSectionHeader(title: "Detail", systemImage: "camera.filters")
        }
        .onAppear {
            if !project.adjustments.detail.isIdentity { showDetail = true }
        }
        .onChange(of: project.adjustments.detail) { _, detail in
            if !detail.isIdentity { showDetail = true }
        }
    }

    private var detailSummary: String {
        project.adjustments.detail.isIdentity
            ? "Hidden until you need them"
            : "Adjustments active"
    }
}

// MARK: - Timelapse

struct DeflickerSection: View {
    @Bindable var project: SequenceProject

    var body: some View {
        Section {
            Toggle(isOn: $project.adjustments.deflicker.enabled) {
                Label("Deflicker", systemImage: "sun.max.trianglebadge.exclamationmark")
            }
            if project.adjustments.deflicker.enabled {
                HStack {
                    Text("Window")
                    Spacer()
                    TextField(
                        "",
                        value: Binding(
                            get: { Double(project.adjustments.deflicker.windowSize) },
                            set: {
                                let odd = Int($0.rounded())
                                project.adjustments.deflicker.windowSize = max(3, odd | 1)
                            }
                        ),
                        format: .number.precision(.fractionLength(0))
                    )
                    .labelsHidden()
                    .multilineTextAlignment(.trailing)
                    .frame(width: 48)
                    .textFieldStyle(.roundedBorder)
                    Text("frames")
                        .foregroundStyle(.secondary)
                    Stepper(
                        "",
                        value: $project.adjustments.deflicker.windowSize,
                        in: 3...61,
                        step: 2
                    )
                    .labelsHidden()
                }
                AdjustmentSliderRow(
                    title: "Strength",
                    value: $project.adjustments.deflicker.strength,
                    range: 0...1,
                    resetValue: 0.75
                )
            }
        } header: {
            PanelSectionHeader(title: "Timelapse", systemImage: "clock.arrow.2.circlepath")
        } footer: {
            Text("Smooths brightness across the in/out range before encoding.")
        }
    }
}

struct UpscaleWarningBanner: View {
    let text: String
    let fitness: ResolutionFitness

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: fitness == .tooSmall
                  ? "exclamationmark.triangle.fill"
                  : "arrow.up.left.and.arrow.down.right")
                .foregroundStyle(color)
                .symbolRenderingMode(.hierarchical)
            Text(text)
                .font(.caption)
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(10)
        .background(color.opacity(0.14), in: RoundedRectangle(cornerRadius: Theme.controlCorner, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: Theme.controlCorner, style: .continuous)
                .strokeBorder(color.opacity(0.28), lineWidth: 1)
        }
        .accessibilityLabel(text)
    }

    private var color: Color {
        switch fitness {
        case .native: return Theme.badgeNative
        case .upscaled: return Theme.badgeUpscaled
        case .tooSmall: return Theme.badgeTooSmall
        }
    }
}
