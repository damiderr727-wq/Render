import UIKit
import SceneKit

// Prozedurale Texturen. Schmutz laeuft ueber die Kachelkante, Teppiche sind
// vollstaendige Perser-Entwuerfe die 1:1 auf die Flaeche gelegt werden.

func makeTex(_ n: Int, _ draw: (CGContext, CGFloat) -> Void) -> UIImage {
    let r = UIGraphicsImageRenderer(size: CGSize(width: n, height: n))
    return r.image { ctx in draw(ctx.cgContext, CGFloat(n)) }
}
func makeTexWH(_ w: Int, _ h: Int, _ draw: (CGContext, CGFloat, CGFloat) -> Void) -> UIImage {
    let r = UIGraphicsImageRenderer(size: CGSize(width: w, height: h))
    return r.image { ctx in draw(ctx.cgContext, CGFloat(w), CGFloat(h)) }
}
private func rnd(_ a: CGFloat, _ b: CGFloat) -> CGFloat { CGFloat.random(in: a...b) }

// --- Schmutz ---

private func stain(_ c: CGContext, _ W: CGFloat, _ H: CGFloat, _ x: CGFloat, _ y: CGFloat, _ r: CGFloat, _ color: UIColor) {
    c.setFillColor(color.cgColor)
    for ox in [-W, 0, W] { for oy in [-H, 0, H] {
        let rect = CGRect(x: x + ox - r, y: y + oy - r, width: r * 2, height: r * 2)
        if rect.maxX < 0 || rect.minX > W || rect.maxY < 0 || rect.minY > H { continue }
        c.fillEllipse(in: rect)
    }}
}
private func grime(_ c: CGContext, _ N: CGFloat, count: Int, alpha: CGFloat) {
    for _ in 0..<count {
        stain(c, N, N, rnd(0, N), rnd(0, N), rnd(N * 0.006, N * 0.042),
              UIColor(white: rnd(0, 0.30), alpha: rnd(alpha * 0.2, alpha)))
    }
}
private func speckle(_ c: CGContext, _ W: CGFloat, _ H: CGFloat, count: Int, alpha: CGFloat = 0.10) {
    for _ in 0..<count {
        c.setFillColor(UIColor(white: rnd(0, 1), alpha: alpha).cgColor)
        c.fill(CGRect(x: rnd(0, W), y: rnd(0, H), width: rnd(1, 2.0), height: rnd(1, 2.0)))
    }
}
private func streaks(_ c: CGContext, _ N: CGFloat, count: Int) {
    for _ in 0..<count {
        let x = rnd(0, N), y0 = rnd(0, N * 0.4), len = rnd(N * 0.2, N * 0.55)
        c.setStrokeColor(UIColor(white: rnd(0.05, 0.25), alpha: rnd(0.03, 0.10)).cgColor)
        c.setLineWidth(rnd(1, 3))
        c.move(to: CGPoint(x: x, y: y0)); c.addLine(to: CGPoint(x: x + rnd(-2, 2), y: y0 + len))
        c.strokePath()
    }
}

func texMat(_ img: UIImage, _ rx: Float, _ ry: Float) -> SCNMaterial {
    let m = SCNMaterial()
    m.lightingModel = .lambert
    m.diffuse.contents = img
    m.diffuse.wrapS = .repeat
    m.diffuse.wrapT = .repeat
    m.diffuse.contentsTransform = SCNMatrix4MakeScale(rx, ry, 1)
    m.diffuse.magnificationFilter = .nearest
    m.diffuse.minificationFilter = .linear
    m.diffuse.mipFilter = .linear
    m.diffuse.maxAnisotropy = 8
    m.locksAmbientWithDiffuse = true
    return m
}

// ============ Perser-Teppiche ============

// Rosette / Palmette
private func rosette(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ r: CGFloat,
                     _ petal: UIColor, _ core: UIColor) {
    c.setFillColor(petal.cgColor)
    for i in 0..<8 {
        let a = CGFloat(i) / 8 * .pi * 2
        let px = x + cos(a) * r * 0.62, py = y + sin(a) * r * 0.62
        c.fillEllipse(in: CGRect(x: px - r * 0.36, y: py - r * 0.36, width: r * 0.72, height: r * 0.72))
    }
    c.setFillColor(core.cgColor)
    c.fillEllipse(in: CGRect(x: x - r * 0.34, y: y - r * 0.34, width: r * 0.68, height: r * 0.68))
}

// Boteh (Paisley-Tropfen)
private func boteh(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ s: CGFloat, _ color: UIColor) {
    c.setFillColor(color.cgColor)
    c.beginPath()
    c.move(to: CGPoint(x: x, y: y + s * 1.05))
    c.addQuadCurve(to: CGPoint(x: x + s * 0.55, y: y), control: CGPoint(x: x + s * 0.80, y: y + s * 0.75))
    c.addQuadCurve(to: CGPoint(x: x, y: y - s * 0.85), control: CGPoint(x: x + s * 0.42, y: y - s * 0.70))
    c.addQuadCurve(to: CGPoint(x: x - s * 0.55, y: y), control: CGPoint(x: x - s * 0.42, y: y - s * 0.70))
    c.addQuadCurve(to: CGPoint(x: x, y: y + s * 1.05), control: CGPoint(x: x - s * 0.80, y: y + s * 0.75))
    c.fillPath()
}

// gelapptes Medaillon
private func medallion(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ rx: CGFloat, _ ry: CGFloat,
                       _ fill: UIColor, _ edge: UIColor, _ lobes: Int) {
    c.setFillColor(fill.cgColor)
    for i in 0..<lobes {
        let a = CGFloat(i) / CGFloat(lobes) * .pi * 2
        let px = x + cos(a) * rx * 0.78, py = y + sin(a) * ry * 0.78
        c.fillEllipse(in: CGRect(x: px - rx * 0.30, y: py - ry * 0.30, width: rx * 0.60, height: ry * 0.60))
    }
    c.fillEllipse(in: CGRect(x: x - rx * 0.82, y: y - ry * 0.82, width: rx * 1.64, height: ry * 1.64))
    c.setStrokeColor(edge.cgColor); c.setLineWidth(max(1.5, rx * 0.045))
    c.strokeEllipse(in: CGRect(x: x - rx * 0.82, y: y - ry * 0.82, width: rx * 1.64, height: ry * 1.64))
    c.strokeEllipse(in: CGRect(x: x - rx * 0.52, y: y - ry * 0.52, width: rx * 1.04, height: ry * 1.04))
}

private func guardBands(_ c: CGContext, _ r: CGRect, _ light: UIColor, _ dark: UIColor, _ w: CGFloat) {
    c.setStrokeColor(dark.cgColor); c.setLineWidth(w * 1.6); c.stroke(r)
    c.setStrokeColor(light.cgColor); c.setLineWidth(w * 0.6)
    c.stroke(r.insetBy(dx: -w * 1.1, dy: -w * 1.1))
    c.stroke(r.insetBy(dx: w * 1.1, dy: w * 1.1))
}

/// Kompletter Perserteppich - wird 1:1 auf die Flaeche gelegt, nicht gekachelt.
func persianRug(field: UIColor, border: UIColor, accent: UIColor,
                light: UIColor, dark: UIColor, size: Int = 512) -> UIImage {
    makeTex(size) { c, N in
        // Bordüre als Grundflaeche
        c.setFillColor(border.cgColor); c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        c.setFillColor(dark.cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N * 0.022))
        c.fill(CGRect(x: 0, y: N * 0.978, width: N, height: N * 0.022))
        c.fill(CGRect(x: 0, y: 0, width: N * 0.022, height: N))
        c.fill(CGRect(x: N * 0.978, y: 0, width: N * 0.022, height: N))

        // Bordüren-Ornament ringsum
        let bMid = N * 0.105
        let step = N / 9
        var t: CGFloat = step * 0.5
        while t < N {
            rosette(c, t, bMid, N * 0.042, accent, light)
            rosette(c, t, N - bMid, N * 0.042, accent, light)
            rosette(c, bMid, t, N * 0.042, accent, light)
            rosette(c, N - bMid, t, N * 0.042, accent, light)
            t += step
        }

        // Feld
        let inset = N * 0.185
        let field_r = CGRect(x: inset, y: inset, width: N - inset * 2, height: N - inset * 2)
        guardBands(c, field_r, light, dark, N * 0.010)
        c.setFillColor(field.cgColor); c.fill(field_r)

        // Allover-Muster im Feld
        let fx = field_r.minX, fy = field_r.minY, fw = field_r.width, fh = field_r.height
        let gs = fw / 6
        for gy in 0..<6 { for gx in 0..<6 {
            let px = fx + (CGFloat(gx) + 0.5) * gs
            let py = fy + (CGFloat(gy) + 0.5) * (fh / 6)
            boteh(c, px, py, gs * 0.20, accent.withAlphaComponent(0.55))
            c.setFillColor(light.withAlphaComponent(0.30).cgColor)
            c.fillEllipse(in: CGRect(x: px - gs * 0.05, y: py - gs * 0.42, width: gs * 0.10, height: gs * 0.10))
        }}
        // Ranken
        c.setStrokeColor(light.withAlphaComponent(0.22).cgColor); c.setLineWidth(N * 0.005)
        for i in 0..<7 {
            let yy = fy + fh * (CGFloat(i) + 0.5) / 7
            c.move(to: CGPoint(x: fx, y: yy))
            var xx = fx
            while xx < fx + fw {
                c.addQuadCurve(to: CGPoint(x: xx + fw / 6, y: yy),
                               control: CGPoint(x: xx + fw / 12, y: yy + (i % 2 == 0 ? -fh * 0.05 : fh * 0.05)))
                xx += fw / 6
            }
            c.strokePath()
        }

        // Eckzwickel
        for cx in [fx + fw * 0.16, fx + fw * 0.84] {
            for cy in [fy + fh * 0.16, fy + fh * 0.84] {
                c.setFillColor(border.withAlphaComponent(0.85).cgColor)
                c.fillEllipse(in: CGRect(x: cx - fw * 0.17, y: cy - fh * 0.17, width: fw * 0.34, height: fh * 0.34))
                rosette(c, cx, cy, fw * 0.075, accent, light)
            }
        }

        // Zentrales Medaillon
        medallion(c, N / 2, N / 2, fw * 0.26, fh * 0.26, border, light, 8)
        rosette(c, N / 2, N / 2, fw * 0.11, accent, light)

        // Abnutzung
        speckle(c, N, N, count: 5200, alpha: 0.07)
        for _ in 0..<260 {
            stain(c, N, N, rnd(0, N), rnd(0, N), rnd(N * 0.004, N * 0.03),
                  UIColor(white: rnd(0, 0.35), alpha: rnd(0.02, 0.11)))
        }
        // Laufspur in der Mitte
        c.setFillColor(UIColor(white: 0, alpha: 0.07).cgColor)
        c.fill(CGRect(x: N * 0.30, y: 0, width: N * 0.40, height: N))
    }
}

/// Laeufer fuer den Flur - schmal und lang, Bordüre nur aussen.
func persianRunner(field: UIColor, border: UIColor, accent: UIColor,
                   light: UIColor, dark: UIColor) -> UIImage {
    makeTexWH(192, 768) { c, W, H in
        c.setFillColor(border.cgColor); c.fill(CGRect(x: 0, y: 0, width: W, height: H))
        c.setFillColor(dark.cgColor)
        c.fill(CGRect(x: 0, y: 0, width: W, height: H * 0.008))
        c.fill(CGRect(x: 0, y: H * 0.992, width: W, height: H * 0.008))
        c.fill(CGRect(x: 0, y: 0, width: W * 0.03, height: H))
        c.fill(CGRect(x: W * 0.97, y: 0, width: W * 0.03, height: H))

        var t: CGFloat = W * 0.16
        while t < H {
            rosette(c, W * 0.115, t, W * 0.062, accent, light)
            rosette(c, W - W * 0.115, t, W * 0.062, accent, light)
            t += W * 0.32
        }

        let inset = W * 0.24
        let f = CGRect(x: inset, y: inset * 0.9, width: W - inset * 2, height: H - inset * 1.8)
        guardBands(c, f, light, dark, W * 0.020)
        c.setFillColor(field.cgColor); c.fill(f)

        // Kette von Medaillons
        let n = 7
        for i in 0..<n {
            let cy = f.minY + f.height * (CGFloat(i) + 0.5) / CGFloat(n)
            medallion(c, W / 2, cy, f.width * 0.36, f.height / CGFloat(n) * 0.36, border, light, 6)
            rosette(c, W / 2, cy, f.width * 0.15, accent, light)
            boteh(c, f.minX + f.width * 0.18, cy + f.height / CGFloat(n) * 0.34, f.width * 0.11, accent.withAlphaComponent(0.6))
            boteh(c, f.maxX - f.width * 0.18, cy + f.height / CGFloat(n) * 0.34, f.width * 0.11, accent.withAlphaComponent(0.6))
        }

        speckle(c, W, H, count: 4200, alpha: 0.07)
        for _ in 0..<220 {
            stain(c, W, H, rnd(0, W), rnd(0, H), rnd(W * 0.008, W * 0.06),
                  UIColor(white: rnd(0, 0.35), alpha: rnd(0.02, 0.11)))
        }
        c.setFillColor(UIColor(white: 0, alpha: 0.08).cgColor)
        c.fill(CGRect(x: W * 0.32, y: 0, width: W * 0.36, height: H))
    }
}

// ============ Boeden / Waende ============

func woodFloorTexture() -> UIImage {
    makeTex(256) { c, N in
        c.setFillColor(UIColor(red: 0.36, green: 0.24, blue: 0.14, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        let rows = 8, ph = N / CGFloat(rows)
        for i in 0..<rows {
            let y = CGFloat(i) * ph, v = rnd(-0.05, 0.05)
            c.setFillColor(UIColor(red: 0.37 + v, green: 0.25 + v, blue: 0.15 + v, alpha: 1).cgColor)
            c.fill(CGRect(x: 0, y: y, width: N, height: ph - 2))
            c.setStrokeColor(UIColor(white: 0, alpha: 0.11).cgColor)
            for _ in 0..<10 {
                let ly = y + rnd(2, ph - 4)
                c.setLineWidth(rnd(0.6, 1.6))
                c.move(to: CGPoint(x: rnd(0, N * 0.6), y: ly))
                c.addLine(to: CGPoint(x: rnd(N * 0.4, N), y: ly + rnd(-1.2, 1.2)))
                c.strokePath()
            }
            c.setFillColor(UIColor(white: 0, alpha: 0.40).cgColor)
            c.fill(CGRect(x: 0, y: y + ph - 2, width: N, height: 2))
            c.fill(CGRect(x: rnd(0, N), y: y, width: 2, height: ph - 2))
        }
        speckle(c, N, N, count: 2200)
        grime(c, N, count: 220, alpha: 0.09)
    }
}

func stoneFloorTexture() -> UIImage {
    makeTex(256) { c, N in
        c.setFillColor(UIColor(white: 0.16, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        let n = 4, t = N / CGFloat(n)
        for gy in 0..<n { for gx in 0..<n {
            let v = rnd(-0.05, 0.05)
            c.setFillColor(UIColor(red: 0.56 + v, green: 0.55 + v, blue: 0.51 + v, alpha: 1).cgColor)
            c.fill(CGRect(x: CGFloat(gx) * t + 2, y: CGFloat(gy) * t + 2, width: t - 4, height: t - 4))
            c.setStrokeColor(UIColor(white: 0.34, alpha: 0.30).cgColor); c.setLineWidth(1)
            for _ in 0..<3 {
                var vx = CGFloat(gx) * t + rnd(4, t - 4), vy = CGFloat(gy) * t + rnd(4, t - 4)
                c.move(to: CGPoint(x: vx, y: vy))
                for _ in 0..<4 { vx += rnd(-9, 9); vy += rnd(-9, 9); c.addLine(to: CGPoint(x: vx, y: vy)) }
                c.strokePath()
            }
        }}
        speckle(c, N, N, count: 2600)
        grime(c, N, count: 200, alpha: 0.07)
    }
}

func wallpaperTexture(_ base: UIColor, _ accent: UIColor) -> UIImage {
    makeTex(256) { c, N in
        c.setFillColor(base.cgColor); c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        c.setFillColor(UIColor(white: 1, alpha: 0.04).cgColor)
        var sx: CGFloat = 0
        while sx < N { c.fill(CGRect(x: sx, y: 0, width: 3, height: N)); sx += 9 }
        let s = N / 8
        for gy in 0..<8 { for gx in 0..<8 {
            let off: CGFloat = (gy % 2 == 0) ? 0 : s / 2
            var px = CGFloat(gx) * s + s / 2 + off
            if px > N { px -= N }
            let py = CGFloat(gy) * s + s / 2
            c.setStrokeColor(accent.withAlphaComponent(0.75).cgColor); c.setLineWidth(1.8)
            c.addArc(center: CGPoint(x: px, y: py), radius: s * 0.30, startAngle: .pi, endAngle: 0, clockwise: false)
            c.strokePath()
            c.setLineWidth(1.3)
            c.addArc(center: CGPoint(x: px - s * 0.30, y: py + s * 0.16), radius: s * 0.15, startAngle: -.pi / 2, endAngle: .pi / 2, clockwise: false)
            c.strokePath()
            c.addArc(center: CGPoint(x: px + s * 0.30, y: py + s * 0.16), radius: s * 0.15, startAngle: .pi / 2, endAngle: -.pi / 2, clockwise: true)
            c.strokePath()
            c.setFillColor(accent.withAlphaComponent(0.65).cgColor)
            c.fillEllipse(in: CGRect(x: px - s * 0.055, y: py - s * 0.14, width: s * 0.11, height: s * 0.11))
        }}
        streaks(c, N, count: 30)
        speckle(c, N, N, count: 2400)
        grime(c, N, count: 280, alpha: 0.08)
    }
}

func tileTexture(_ base: UIColor, _ n: Int) -> UIImage {
    makeTex(256) { c, N in
        c.setFillColor(UIColor(white: 0.22, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        let t = N / CGFloat(n)
        var br: CGFloat = 0, bg: CGFloat = 0, bb: CGFloat = 0, ba: CGFloat = 0
        base.getRed(&br, green: &bg, blue: &bb, alpha: &ba)
        for gy in 0..<n { for gx in 0..<n {
            let v = rnd(-0.045, 0.045)
            c.setFillColor(UIColor(red: br + v, green: bg + v, blue: bb + v, alpha: 1).cgColor)
            c.fill(CGRect(x: CGFloat(gx) * t + 1.5, y: CGFloat(gy) * t + 1.5, width: t - 3, height: t - 3))
            c.setFillColor(UIColor(white: 1, alpha: 0.10).cgColor)
            c.fill(CGRect(x: CGFloat(gx) * t + 1.5, y: CGFloat(gy) * t + 1.5, width: t - 3, height: 2))
            c.fill(CGRect(x: CGFloat(gx) * t + 1.5, y: CGFloat(gy) * t + 1.5, width: 2, height: t - 3))
        }}
        speckle(c, N, N, count: 1800)
        grime(c, N, count: 300, alpha: 0.11)
        streaks(c, N, count: 16)
    }
}

func wainscotTexture() -> UIImage {
    makeTex(128) { c, N in
        c.setFillColor(UIColor(red: 0.26, green: 0.17, blue: 0.10, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        let cols = 3, w = N / CGFloat(cols)
        for i in 0..<cols {
            let x = CGFloat(i) * w
            c.setFillColor(UIColor(red: 0.31, green: 0.21, blue: 0.12, alpha: 1).cgColor)
            c.fill(CGRect(x: x + 6, y: 15, width: w - 12, height: N - 34))
            c.setStrokeColor(UIColor(white: 0, alpha: 0.45).cgColor); c.setLineWidth(2)
            c.stroke(CGRect(x: x + 6, y: 15, width: w - 12, height: N - 34))
            c.setStrokeColor(UIColor(white: 1, alpha: 0.07).cgColor); c.setLineWidth(1)
            c.stroke(CGRect(x: x + 9, y: 18, width: w - 18, height: N - 40))
        }
        c.setFillColor(UIColor(red: 0.35, green: 0.24, blue: 0.14, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: 10))
        c.setFillColor(UIColor(white: 0, alpha: 0.35).cgColor)
        c.fill(CGRect(x: 0, y: 10, width: N, height: 3))
        speckle(c, N, N, count: 1100)
        grime(c, N, count: 120, alpha: 0.10)
    }
}

func plankWoodTexture() -> UIImage {
    makeTex(128) { c, N in
        c.setFillColor(UIColor(red: 0.38, green: 0.25, blue: 0.14, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        for _ in 0..<34 {
            let y = rnd(0, N)
            c.setStrokeColor(UIColor(white: 0, alpha: rnd(0.07, 0.22)).cgColor)
            c.setLineWidth(rnd(0.5, 1.8))
            c.move(to: CGPoint(x: 0, y: y)); c.addLine(to: CGPoint(x: N, y: y + rnd(-2, 2)))
            c.strokePath()
        }
        speckle(c, N, N, count: 1200)
        grime(c, N, count: 110, alpha: 0.09)
    }
}

func plasterTexture() -> UIImage {
    makeTex(128) { c, N in
        c.setFillColor(UIColor(red: 0.50, green: 0.49, blue: 0.45, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        speckle(c, N, N, count: 2400, alpha: 0.08)
        grime(c, N, count: 190, alpha: 0.055)
        c.setStrokeColor(UIColor(white: 0.22, alpha: 0.20).cgColor); c.setLineWidth(0.8)
        for _ in 0..<8 {
            var x = rnd(0, N), y = rnd(0, N)
            c.move(to: CGPoint(x: x, y: y))
            for _ in 0..<5 { x += rnd(-14, 14); y += rnd(-14, 14); c.addLine(to: CGPoint(x: x, y: y)) }
            c.strokePath()
        }
    }
}

func grungeTexture() -> UIImage {
    makeTex(128) { c, N in
        c.setFillColor(UIColor(white: 0.97, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
        for _ in 0..<200 {
            stain(c, N, N, rnd(0, N), rnd(0, N), rnd(N * 0.008, N * 0.045),
                  UIColor(white: rnd(0.58, 0.92), alpha: rnd(0.05, 0.16)))
        }
        speckle(c, N, N, count: 3000, alpha: 0.06)
    }
}

// Laedt ein PNG aus dem Projekt. Fehlt die Datei, wird die prozedurale
// Fassung benutzt - so laeuft das Spiel auch ohne importierte Bilder weiter.
private func load(_ name: String, _ fallback: () -> UIImage) -> UIImage {
    UIImage(named: name) ?? fallback()
}
func flatTexture(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat) -> UIImage {
    makeTex(8) { c, N in
        c.setFillColor(UIColor(red: r, green: g, blue: b, alpha: 1).cgColor)
        c.fill(CGRect(x: 0, y: 0, width: N, height: N))
    }
}

enum Tex {
    static let woodFloor  = load("wood_floor",  woodFloorTexture)
    static let stoneFloor = load("stone_floor", stoneFloorTexture)
    static let plankWood  = load("plank",       plankWoodTexture)
    static let wainscot   = load("wainscot",    wainscotTexture)
    static let plaster    = load("plaster",     plasterTexture)
    static let grunge     = load("grunge", grungeTexture)

    static let tileWhite = load("tile_white") { tileTexture(UIColor(red: 0.70, green: 0.70, blue: 0.66, alpha: 1), 8) }
    static let tileGreen = load("tile_green") { tileTexture(UIColor(red: 0.52, green: 0.58, blue: 0.52, alpha: 1), 8) }

    static let wpGreen = load("wp_green") { wallpaperTexture(UIColor(red: 0.40, green: 0.46, blue: 0.38, alpha: 1), UIColor(red: 0.62, green: 0.69, blue: 0.57, alpha: 1)) }
    static let wpRed   = load("wp_red")   { wallpaperTexture(UIColor(red: 0.48, green: 0.32, blue: 0.28, alpha: 1), UIColor(red: 0.70, green: 0.51, blue: 0.44, alpha: 1)) }
    static let wpOlive = load("wp_olive") { wallpaperTexture(UIColor(red: 0.45, green: 0.43, blue: 0.32, alpha: 1), UIColor(red: 0.66, green: 0.62, blue: 0.47, alpha: 1)) }
    static let wpBeige = load("wp_beige") { wallpaperTexture(UIColor(red: 0.50, green: 0.46, blue: 0.37, alpha: 1), UIColor(red: 0.70, green: 0.64, blue: 0.52, alpha: 1)) }
    static let wpBlue  = load("wp_blue")  { wallpaperTexture(UIColor(red: 0.36, green: 0.40, blue: 0.47, alpha: 1), UIColor(red: 0.55, green: 0.61, blue: 0.71, alpha: 1)) }
    static let wpBrown = load("wp_brown") { wallpaperTexture(UIColor(red: 0.44, green: 0.37, blue: 0.30, alpha: 1), UIColor(red: 0.64, green: 0.55, blue: 0.44, alpha: 1)) }

    static let rugRed = load("rug_red") { persianRug(
        field:  UIColor(red: 0.46, green: 0.13, blue: 0.11, alpha: 1),
        border: UIColor(red: 0.18, green: 0.16, blue: 0.26, alpha: 1),
        accent: UIColor(red: 0.78, green: 0.64, blue: 0.34, alpha: 1),
        light:  UIColor(red: 0.88, green: 0.82, blue: 0.68, alpha: 1),
        dark:   UIColor(red: 0.12, green: 0.08, blue: 0.07, alpha: 1)) }
    static let rugBlue = load("rug_blue") { persianRug(
        field:  UIColor(red: 0.14, green: 0.20, blue: 0.32, alpha: 1),
        border: UIColor(red: 0.42, green: 0.15, blue: 0.14, alpha: 1),
        accent: UIColor(red: 0.72, green: 0.62, blue: 0.38, alpha: 1),
        light:  UIColor(red: 0.84, green: 0.80, blue: 0.66, alpha: 1),
        dark:   UIColor(red: 0.07, green: 0.09, blue: 0.14, alpha: 1)) }
    static let rugGold = load("rug_gold") { persianRug(
        field:  UIColor(red: 0.40, green: 0.32, blue: 0.17, alpha: 1),
        border: UIColor(red: 0.30, green: 0.12, blue: 0.12, alpha: 1),
        accent: UIColor(red: 0.66, green: 0.36, blue: 0.24, alpha: 1),
        light:  UIColor(red: 0.86, green: 0.79, blue: 0.60, alpha: 1),
        dark:   UIColor(red: 0.13, green: 0.10, blue: 0.06, alpha: 1)) }
    static let runner = load("runner") { persianRunner(
        field:  UIColor(red: 0.42, green: 0.14, blue: 0.12, alpha: 1),
        border: UIColor(red: 0.16, green: 0.18, blue: 0.26, alpha: 1),
        accent: UIColor(red: 0.76, green: 0.62, blue: 0.34, alpha: 1),
        light:  UIColor(red: 0.86, green: 0.80, blue: 0.66, alpha: 1),
        dark:   UIColor(red: 0.10, green: 0.07, blue: 0.06, alpha: 1)) }

    // Gemaelde - werden von picture() zufaellig verteilt
    static let art: [UIImage] = [
        load("art_portrait")  { flatTexture(0.20, 0.16, 0.13) },
        load("art_landscape") { flatTexture(0.18, 0.18, 0.15) },
        load("art_still")     { flatTexture(0.16, 0.13, 0.11) },
        load("art_dark")      { flatTexture(0.12, 0.13, 0.17) },
    ]
    /// stormWindow waehlt anhand der Position aus, damit sich
    /// kein Fenster wiederholt - vorher war in allen sieben derselbe Mond.
    /// Drei gleissend helle Wolkenscheiben und eine Sturmscheibe. Man sieht
    /// nie eine Aussenwelt - die Fenster leuchten oder sind schwarz.
    static let windows: [UIImage] = [
        load("window_day")   { flatTexture(0.88, 0.89, 0.91) },
        load("window_day2")  { flatTexture(0.90, 0.89, 0.90) },
        load("window_day3")  { flatTexture(0.86, 0.87, 0.90) },
        load("window_storm") { flatTexture(0.08, 0.10, 0.13) },
    ]
    static let windowNight = windows[0]

    // Koerper-Materialien der Figur
    static let skin       = load("skin")        { flatTexture(0.78, 0.60, 0.47) }
    static let clothShirt = load("cloth_shirt") { flatTexture(0.48, 0.55, 0.65) }
    static let clothVest  = load("cloth_vest")  { flatTexture(0.19, 0.23, 0.33) }
    static let clothPants = load("cloth_pants") { flatTexture(0.18, 0.21, 0.29) }
    static let leather    = load("leather")     { flatTexture(0.13, 0.12, 0.13) }
    static let hair       = load("hair")        { flatTexture(0.28, 0.19, 0.11) }
    static let felt       = load("felt")        { flatTexture(0.16, 0.19, 0.29) }

    // Metall und Sanitaer
    static let brass      = load("brass")       { flatTexture(0.55, 0.45, 0.20) }
    static let enamel     = load("enamel")      { flatTexture(0.78, 0.78, 0.75) }
    static let enamelFoul = load("enamel_foul") { flatTexture(0.42, 0.30, 0.24) }

    // Gesicht: komplett aufgemalt, liegt nur auf der Vorderseite des Kopfkastens
    static let face    = load("face")    { flatTexture(0.78, 0.60, 0.47) }
    static let marble  = load("marble")  { flatTexture(0.70, 0.69, 0.65) }
    /// Vier Tuertypen. doorLeaf waehlt anhand des Stils.
    static let doors: [UIImage] = [
        load("door")        { flatTexture(0.30, 0.20, 0.11) },   // Kassette, Wohnbereich
        load("door_glazed") { flatTexture(0.28, 0.20, 0.12) },   // Milchglas, Buero
        load("door_metal")  { flatTexture(0.26, 0.28, 0.26) },   // Blech, Technik
        load("door_padded") { flatTexture(0.24, 0.11, 0.11) },   // gepolstert, Direktion
    ]
    static let door = doors[0]
    static let books   = load("books")   { flatTexture(0.28, 0.18, 0.15) }
    static let curtain = load("curtain") { flatTexture(0.32, 0.14, 0.13) }
    static let iron    = load("iron")    { flatTexture(0.16, 0.15, 0.15) }
    static let mirror  = load("mirror")  { flatTexture(0.40, 0.44, 0.46) }
    static let concrete  = load("concrete")   { flatTexture(0.45, 0.44, 0.41) }
    static let brick     = load("brick")      { flatTexture(0.42, 0.24, 0.19) }
    static let rust      = load("rust")       { flatTexture(0.42, 0.24, 0.13) }
    static let waterFoul = load("water_foul") { flatTexture(0.28, 0.11, 0.08) }

    // Hilfsbilder fuer die Lichteffekte (werden additiv gemischt)
    static let shaft   = load("shaft") { flatTexture(0.5, 0.5, 0.5) }
    static let pool    = load("pool")  { flatTexture(0.5, 0.5, 0.5) }
    static let dust    = load("dust")  { flatTexture(0.9, 0.9, 0.9) }

    // Polster und Boeden
    static let velvet      = load("velvet")       { flatTexture(0.34, 0.13, 0.14) }
    static let velvetGreen = load("velvet_green") { flatTexture(0.15, 0.25, 0.18) }
    static let damaskUph   = load("damask_uph")   { flatTexture(0.22, 0.19, 0.15) }
    static let parquet     = load("parquet")      { flatTexture(0.34, 0.22, 0.13) }
    static let sheer       = load("sheer")        { flatTexture(0.72, 0.73, 0.70) }
    static let glass       = load("glass")        { flatTexture(0.12, 0.14, 0.17) }
    static let shadowBlob  = load("shadow_blob")  { flatTexture(0.0, 0.0, 0.0) }
    static let poster1     = load("poster1")      { flatTexture(0.75, 0.68, 0.52) }
    static let poster2     = load("poster2")      { flatTexture(0.75, 0.68, 0.52) }
    static let footprints  = load("footprints")   { flatTexture(0.2, 0.25, 0.3) }
    static let lanternGlass = load("lantern_glass") { flatTexture(0.95, 0.72, 0.35) }
}
