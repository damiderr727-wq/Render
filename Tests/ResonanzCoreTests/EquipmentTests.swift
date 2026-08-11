import XCTest
@testable import ResonanzCore

/// Prueft, was sie traegt: Fassung, Kern, Klinge, Siegel - und dass sich
/// alles davon bis in die Physik durchschlaegt statt nur in einer Tabelle
/// zu stehen.
final class EquipmentTests: XCTestCase {

    /// Ein Spielstand, der die genannte Fassung besitzt und traegt.
    private func stand(_ equipmentID: String, worn: Bool = true) -> SaveState {
        var save = SaveState()
        save.progression.equipmentOwned.insert(equipmentID)
        if worn { save.progression.equipmentWorn = equipmentID }
        return save
    }

    private func stats(_ equipment: Equipment,
                       kern: Kern = .stimmgabel,
                       siegel: [Siegel] = []) -> Stats {
        Stats(equipment: equipment, kern: kern, siegel: siegel)
    }

    /// Wie weit ein Ton fliegt, bevor er vergeht.
    private func reichweite(_ s: Stats) -> Double {
        s.ranged.speed * s.ranged.lifetime
    }

    // MARK: - Der Mantel und die Stimmgabel

    func testMantelUndStimmgabelVerschiebenNichts() {
        let s = stats(EquipmentCatalog.mantel, kern: .stimmgabel)
        XCTAssertEqual(s.runSpeed, Tuning.runSpeed, accuracy: 0.0001)
        XCTAssertEqual(s.jumpVelocity, Tuning.jumpVelocity, accuracy: 0.0001)
        XCTAssertEqual(s.dashSpeed, Tuning.dashSpeed, accuracy: 0.0001)
        XCTAssertEqual(s.resonanceRegen, Tuning.resonanceRegen, accuracy: 0.0001)
        XCTAssertEqual(s.maxHealth(crystals: 5), 10, "Fuenf Kristalle sind zehn Haelften")
        XCTAssertEqual(s.melee.reach, Kampfstil.bogen.melee.reach, accuracy: 0.0001)
        XCTAssertEqual(s.melee.damage, Kampfstil.bogen.melee.damage)
        XCTAssertEqual(s.ranged.damage, Tuning.ranged(.stimmgabel).damage)
    }

    func testOhneGueltigeFassungStehtSieDaWieSieAufgewachtIst() {
        var progression = Progression()
        XCTAssertEqual(progression.equipment.id, EquipmentCatalog.ohne.id,
                       "So faengt das Spiel an")
        progression.equipmentWorn = "gibt_es_nicht"
        XCTAssertEqual(progression.equipment.id, EquipmentCatalog.ohne.id)
        progression.klingeWorn = "gibt_es_nicht"
        XCTAssertEqual(progression.klinge.id, KlingenKatalog.schlicht.id)
    }

    // MARK: - Druck und Oeffnungen

    func testEngeFassungTraegtWeitUndSchlaegtKurz() {
        let mantel = stats(EquipmentCatalog.mantel)
        let eng = stats(EquipmentCatalog.engeFassung)

        XCTAssertGreaterThan(reichweite(eng), reichweite(mantel) * 1.2)
        XCTAssertGreaterThan(eng.ranged.damage, mantel.ranged.damage)
        XCTAssertLessThan(eng.runSpeed, mantel.runSpeed)
        XCTAssertGreaterThan(eng.ranged.cost, mantel.ranged.cost)
    }

    func testOffeneFassungKehrtDasVerhaeltnisUm() {
        let mantel = stats(EquipmentCatalog.mantel)
        let offen = stats(EquipmentCatalog.offeneFassung)

        XCTAssertLessThan(reichweite(offen), reichweite(mantel))
        XCTAssertLessThan(offen.ranged.cost, mantel.ranged.cost)
        XCTAssertGreaterThan(offen.resonanceRegen, mantel.resonanceRegen)
    }

    func testSchlagfassungGibtWuchtUndNimmtSprunghoehe() {
        let mantel = stats(EquipmentCatalog.mantel)
        let schlag = stats(EquipmentCatalog.schlagfassung)

        XCTAssertGreaterThan(schlag.slamRadius, mantel.slamRadius)
        XCTAssertGreaterThan(schlag.slamDamage, mantel.slamDamage)
        // Nach oben faellt der Sprung kuerzer aus - jumpVelocity ist negativ.
        XCTAssertGreaterThan(schlag.jumpVelocity, mantel.jumpVelocity)
    }

    func testGerissenesGewandIstSchnellUndZerbrechlich() {
        let mantel = stats(EquipmentCatalog.mantel)
        let riss = stats(EquipmentCatalog.gerissenesGewand)

        XCTAssertGreaterThan(riss.runSpeed, mantel.runSpeed)
        XCTAssertGreaterThan(riss.dashSpeed, mantel.dashSpeed)
        XCTAssertLessThan(riss.maxHealth(crystals: 5), mantel.maxHealth(crystals: 5))
        XCTAssertGreaterThanOrEqual(riss.maxHealth(crystals: 5), 1)
    }

    // MARK: - Der Kampfstil kommt aus der Fassung

    func testJedeFassungBringtIhrenEigenenSchlagMit() {
        let stich = stats(EquipmentCatalog.engeFassung)     // .stich
        let wirbel = stats(EquipmentCatalog.offeneFassung)  // .wirbel
        let sturz = stats(EquipmentCatalog.schlagfassung)   // .sturz
        let hetze = stats(EquipmentCatalog.cape)            // .hetze

        XCTAssertEqual(EquipmentCatalog.engeFassung.stil, .stich)
        // Der Stich reicht weiter als der Wirbel, trifft dafuer schmaler.
        XCTAssertGreaterThan(stich.melee.reach, wirbel.melee.reach)
        XCTAssertLessThan(stich.melee.halfHeight, wirbel.melee.halfHeight)
        // Rundum trifft rundum.
        XCTAssertEqual(wirbel.melee.shape, .radial)
        // Der Sturz schlaegt am haertesten und am langsamsten.
        XCTAssertGreaterThan(sturz.melee.damage, hetze.melee.damage)
        XCTAssertGreaterThan(sturz.melee.cooldown, hetze.melee.cooldown)
    }

    func testDieKlingeAendertNurDasAussehen() {
        var mitSchlicht = Progression()
        var mitGlas = Progression()
        mitGlas.klingenOwned.insert(KlingenKatalog.glas.id)
        mitGlas.klingeWorn = KlingenKatalog.glas.id

        XCTAssertNotEqual(mitSchlicht.klinge.effect, mitGlas.klinge.effect)
        XCTAssertEqual(mitSchlicht.stats.melee.damage, mitGlas.stats.melee.damage)
        XCTAssertEqual(mitSchlicht.stats.melee.reach, mitGlas.stats.melee.reach,
                       accuracy: 0.0001)
        XCTAssertEqual(mitSchlicht.stats.melee.cooldown, mitGlas.stats.melee.cooldown,
                       accuracy: 0.0001)
        mitSchlicht.klingeWorn = KlingenKatalog.gezackt.id
        XCTAssertEqual(mitSchlicht.klinge.id, KlingenKatalog.schlicht.id,
                       "Was man nicht gefunden hat, fuehrt man auch nicht")
    }

    // MARK: - Der Kern

    func testDerKernBestimmtDenMagiestil() {
        let mantel = EquipmentCatalog.mantel
        let gabel = stats(mantel, kern: .stimmgabel)
        let leier = stats(mantel, kern: .leier)
        let trommel = stats(mantel, kern: .trommel)
        let floete = stats(mantel, kern: .floete)

        XCTAssertEqual(leier.ranged.count, 3, "Die Leier ist ein Dreiklang")
        XCTAssertEqual(gabel.ranged.count, 2)
        XCTAssertGreaterThan(trommel.ranged.damage, floete.ranged.damage)
        XCTAssertGreaterThan(floete.ranged.speed, trommel.ranged.speed)
        // Der Kern verschiebt auch ihre Anlage, nicht nur den Schuss.
        XCTAssertGreaterThan(floete.runSpeed, trommel.runSpeed)
        XCTAssertGreaterThan(trommel.maxHealth(crystals: 5), floete.maxHealth(crystals: 5))
    }

    func testDerKernAendertDenNahkampfNicht() {
        let mantel = EquipmentCatalog.mantel
        let a = stats(mantel, kern: .trommel).melee
        let b = stats(mantel, kern: .floete).melee
        // Beide tragen dieselbe Fassung, also schlagen sie gleich weit.
        XCTAssertEqual(a.reach, b.reach, accuracy: 0.0001)
        XCTAssertEqual(a.shape, b.shape)
    }

    // MARK: - Siegel

    func testSiegelMultiplizierenSichAufDenRest() {
        let ohne = stats(EquipmentCatalog.mantel)
        let mit = stats(EquipmentCatalog.mantel, siegel: [SiegelKatalog.nachhall])
        XCTAssertGreaterThan(reichweite(mit), reichweite(ohne))

        let zwei = stats(EquipmentCatalog.mantel,
                         siegel: [SiegelKatalog.federstaub, SiegelKatalog.windschliff])
        XCTAssertLessThan(zwei.jumpVelocity, ohne.jumpVelocity, "Beide heben sie an")
        XCTAssertGreaterThan(zwei.runSpeed, ohne.runSpeed)
        XCTAssertLessThan(zwei.maxHealth(crystals: 5), ohne.maxHealth(crystals: 5))
    }

    func testKerbenBegrenzenWasManTraegt() {
        var p = Progression()
        p.siegelOwned = Set(SiegelKatalog.all.map(\.id))
        XCTAssertEqual(p.kerbenTotal, 3)

        XCTAssertTrue(p.anlegen(SiegelKatalog.nachhall.id))     // 1
        XCTAssertTrue(p.anlegen(SiegelKatalog.dauerton.id))     // +2 = 3
        XCTAssertEqual(p.kerbenFrei, 0)
        XCTAssertFalse(p.anlegen(SiegelKatalog.federstaub.id),
                       "Keine Kerbe mehr frei")
        XCTAssertFalse(p.anlegen(SiegelKatalog.nachhall.id),
                       "Zweimal dasselbe Siegel geht nicht")

        XCTAssertTrue(p.ablegen(SiegelKatalog.dauerton.id))
        XCTAssertEqual(p.kerbenFrei, 2)
        XCTAssertTrue(p.anlegen(SiegelKatalog.federstaub.id))
        XCTAssertEqual(p.kerbenBelegt, 2)
    }

    func testWasManNichtGefundenHatKannManNichtAnlegen() {
        var p = Progression()
        XCTAssertFalse(p.anlegen(SiegelKatalog.nachhall.id))
        XCTAssertTrue(p.siegelWorn.isEmpty)
    }

    // MARK: - Nichts darf unspielbar werden

    func testJedeKombinationBleibtSpielbar() {
        for equipment in EquipmentCatalog.all {
            for kern in Kern.allCases {
                // Der teuerste tragbare Satz Siegel.
                let s = Stats(equipment: equipment, kern: kern,
                              siegel: [SiegelKatalog.windschliff])
                // Null Oeffnungen hat genau eine: "ohne". Das ist kein
                // geschlossenes Gefaess, sondern gar keines.
                XCTAssertGreaterThanOrEqual(equipment.openings, 0, equipment.id)
                XCTAssertGreaterThan(s.runSpeed, 0, equipment.id)
                XCTAssertLessThan(s.jumpVelocity, 0, equipment.id)
                XCTAssertGreaterThanOrEqual(s.maxHealth(crystals: 5), 1, equipment.id)
                XCTAssertGreaterThan(s.melee.reach, 0, equipment.id)
                XCTAssertGreaterThanOrEqual(s.melee.damage, 1, equipment.id)
                XCTAssertGreaterThan(s.ranged.speed, 0, equipment.id)
                XCTAssertGreaterThan(s.ranged.lifetime, 0, equipment.id)
                XCTAssertGreaterThanOrEqual(s.ranged.damage, 1, equipment.id)
                XCTAssertGreaterThan(s.ranged.cost, 0, equipment.id)
            }
        }
    }

    // MARK: - Die Fassung wirkt bis in die Physik

    func testDieFassungAendertDenLauf() throws {
        let catalog = try WorldCatalog()

        func weite(_ equipmentID: String) throws -> Double {
            let sim = try GameSimulation(catalog: catalog, save: stand(equipmentID))
            _ = sim.update(dt: 1.0 / 60, input: .neutral)
            let start = sim.player.position.x
            for _ in 0..<60 {
                _ = sim.update(dt: 1.0 / 60, input: PlayerInput(moveX: 1))
            }
            return sim.player.position.x - start
        }

        let mitMantel = try weite(EquipmentCatalog.mantel.id)
        let mitRiss = try weite(EquipmentCatalog.gerissenesGewand.id)
        let mitEnge = try weite(EquipmentCatalog.engeFassung.id)

        XCTAssertGreaterThan(mitRiss, mitMantel * 1.1, "Das gerissene Gewand laeuft schneller")
        XCTAssertLessThan(mitEnge, mitMantel * 0.95, "Die enge Fassung ist traege")
    }

    func testDerZusammenhaltBestimmtDieLebenspunkte() throws {
        let catalog = try WorldCatalog()
        let mitMantel = try GameSimulation.newGame(catalog: catalog)
        let mitRiss = try GameSimulation(
            catalog: catalog, save: stand(EquipmentCatalog.gerissenesGewand.id))

        XCTAssertLessThan(mitRiss.player.maxHealth, mitMantel.player.maxHealth)
        XCTAssertGreaterThanOrEqual(mitRiss.player.maxHealth, 1)
        XCTAssertEqual(mitRiss.player.health, mitRiss.player.maxHealth,
                       "Sie startet nicht angeschlagen, nur zerbrechlicher")
    }

    // MARK: - Umziehen

    func testUmziehenNurAnDerStimmgabel() throws {
        let sim = try GameSimulation(
            catalog: try WorldCatalog(),
            save: stand(EquipmentCatalog.engeFassung.id, worn: false))
        _ = sim.update(dt: 1.0 / 60, input: .neutral)

        XCTAssertFalse(sim.wear(EquipmentCatalog.engeFassung.id),
                       "Mitten im Raum ist das kein Kleiderwechsel, sondern ein Umbau")
        XCTAssertEqual(sim.save.progression.equipmentWorn, EquipmentCatalog.ohne.id)

        sim.player.beginRest()
        XCTAssertTrue(sim.wear(EquipmentCatalog.engeFassung.id))
        XCTAssertEqual(sim.save.progression.equipmentWorn, EquipmentCatalog.engeFassung.id)
        XCTAssertEqual(sim.player.stats.equipment.id, EquipmentCatalog.engeFassung.id)
        XCTAssertEqual(sim.player.stats.melee.shape, Kampfstil.stich.melee.shape,
                       "Mit der Fassung wechselt auch der Schlag")
    }

    func testWasManNichtHatKannManNichtTragen() throws {
        let sim = try GameSimulation.newGame(catalog: try WorldCatalog())
        sim.player.beginRest()
        XCTAssertFalse(sim.wear(EquipmentCatalog.schlagfassung.id))
        XCTAssertFalse(sim.wear("gibt_es_nicht"))
        XCTAssertEqual(sim.save.progression.equipmentWorn, EquipmentCatalog.ohne.id)
    }

    // MARK: - In der Welt

    func testJedeFassungLiegtGenauEinmalInDerWelt() throws {
        let catalog = try WorldCatalog()
        var gefunden: [String: Int] = [:]
        for room in try catalog.loadAll() {
            for pickup in room.data.pickups where pickup.kind == "equipment" {
                XCTAssertNotNil(EquipmentCatalog.find(pickup.id),
                                "\(room.id): unbekannte Fassung \(pickup.id)")
                gefunden[pickup.id, default: 0] += 1
            }
        }
        for equipment in EquipmentCatalog.all where equipment.id != EquipmentCatalog.ohne.id {
            XCTAssertEqual(gefunden[equipment.id], 1,
                           "\(equipment.id) muss genau einmal in der Welt liegen")
        }
        XCTAssertNil(gefunden[EquipmentCatalog.ohne.id],
                     "Ohne alles faengt sie an - das liegt nirgends herum")
    }

    func testJedesSiegelUndJedeKlingeLiegenGenauEinmalInDerWelt() throws {
        let catalog = try WorldCatalog()
        var siegel: [String: Int] = [:]
        var klingen: [String: Int] = [:]
        var kerne: [String: Int] = [:]
        for room in try catalog.loadAll() {
            for pickup in room.data.pickups {
                switch pickup.kind {
                case "siegel":
                    XCTAssertNotNil(SiegelKatalog.find(pickup.id),
                                    "\(room.id): unbekanntes Siegel \(pickup.id)")
                    siegel[pickup.id, default: 0] += 1
                case "klinge":
                    XCTAssertNotNil(KlingenKatalog.find(pickup.id),
                                    "\(room.id): unbekannte Klinge \(pickup.id)")
                    klingen[pickup.id, default: 0] += 1
                case "kern":
                    XCTAssertNotNil(Kern(rawValue: pickup.id),
                                    "\(room.id): unbekannter Kern \(pickup.id)")
                    kerne[pickup.id, default: 0] += 1
                default:
                    break
                }
            }
        }
        for s in SiegelKatalog.all {
            XCTAssertEqual(siegel[s.id], 1, "\(s.id) muss genau einmal liegen")
        }
        for k in KlingenKatalog.all where k.id != KlingenKatalog.schlicht.id {
            XCTAssertEqual(klingen[k.id], 1, "\(k.id) muss genau einmal liegen")
        }
        for k in Kern.allCases where k != .stimmgabel {
            XCTAssertEqual(kerne[k.rawValue], 1, "\(k.rawValue) muss genau einmal liegen")
        }
        XCTAssertNil(kerne[Kern.stimmgabel.rawValue],
                     "Die Stimmgabel steckt von Anfang an in ihr")
    }

    /// Die Kerben muessen knapp bleiben: wer alles gefundene zugleich
    /// tragen koennte, muesste nie waehlen.
    func testAlleSiegelZusammenPassenNichtInDieKerben() {
        let alle = SiegelKatalog.kosten(SiegelKatalog.all.map(\.id))
        XCTAssertGreaterThan(alle, Progression().kerbenTotal * 2,
                             "Sonst ist die Auswahl keine Entscheidung")
    }

    /// Fuer das Inventar muss es sie ohne alles geben: nur die Nadeln, die
    /// Flamme und der Kern, der gerade in ihr steckt. Daran sieht man beim
    /// Anlegen, was von ihr selbst kommt und was von der Fassung.
    func testEsGibtSieAuchOhneAlles() throws {
        struct Sheet: Decodable { let frames: [String: [String: Double]] }
        let sheet = try Resources.decode(Sheet.self, subdirectory: "Atlas", name: "characters")
        for kern in Kern.allCases {
            for zustand in Bildnis.zustaende {
                let key = Bildnis.nackt(kern: kern, zustand: zustand) + "_0"
                XCTAssertNotNil(sheet.frames[key], "Es fehlt das Bild \(key)")
            }
        }
    }

    /// Die Fassung wird gezeichnet, nicht nur gerechnet: zu jeder muss es
    /// auch Bilder geben, sonst greift die Darstellung ins Leere.
    func testZuJederFassungGibtEsBilder() throws {
        struct Sheet: Decodable { let frames: [String: [String: Double]] }
        let sheet = try Resources.decode(Sheet.self, subdirectory: "Atlas", name: "characters")
        for equipment in EquipmentCatalog.all {
            for kern in Kern.allCases {
                for zustand in Bildnis.zustaende {
                    let key = Bildnis.sprite(kern: kern, fassung: equipment.id,
                                             zustand: zustand) + "_0"
                    XCTAssertNotNil(sheet.frames[key], "Es fehlt das Bild \(key)")
                }
            }
        }
    }
}
