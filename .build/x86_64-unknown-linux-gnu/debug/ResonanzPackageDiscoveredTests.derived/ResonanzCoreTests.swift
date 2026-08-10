import XCTest
@testable import ResonanzCoreTests

fileprivate extension PhysicsTests {
    @available(*, deprecated, message: "Not actually deprecated. Marked as deprecated to allow inclusion of deprecated tests (which test deprecated functionality) without warnings")
    static nonisolated(unsafe) let __allTests__PhysicsTests = [
        ("testDashMachtKurzUnverwundbar", testDashMachtKurzUnverwundbar),
        ("testDoppelsprungKommtHoeher", testDoppelsprungKommtHoeher),
        ("testFaelltAufDenBodenUndBleibtLiegen", testFaelltAufDenBodenUndBleibtLiegen),
        ("testFigurBleibtImRaum", testFigurBleibtImRaum),
        ("testHerzschlagTraegtWeiterAlsEinSprung", testHerzschlagTraegtWeiterAlsEinSprung),
        ("testKlangschrittHaeltAnDerWand", testKlangschrittHaeltAnDerWand),
        ("testLandetBuendigAufDemBoden", testLandetBuendigAufDemBoden),
        ("testOhneFluegelschlagKeinZweiterSprung", testOhneFluegelschlagKeinZweiterSprung),
        ("testPlattformTraegtVonObenUndLaesstVonUntenDurch", testPlattformTraegtVonObenUndLaesstVonUntenDurch),
        ("testSprunghoeheEntsprichtDerAuslegung", testSprunghoeheEntsprichtDerAuslegung),
        ("testTrefferKostetLebenUndStoesstZurueck", testTrefferKostetLebenUndStoesstZurueck)
    ]
}

fileprivate extension ProgressionTests {
    @available(*, deprecated, message: "Not actually deprecated. Marked as deprecated to allow inclusion of deprecated tests (which test deprecated functionality) without warnings")
    static nonisolated(unsafe) let __allTests__ProgressionTests = [
        ("testBossraumIstErreichbar", testBossraumIstErreichbar),
        ("testFaehigkeitenLiegenInEinerSpielbarenReihenfolge", testFaehigkeitenLiegenInEinerSpielbarenReihenfolge),
        ("testInstrumentenreihenfolgeIstStabil", testInstrumentenreihenfolgeIstStabil),
        ("testJederRaumIstMitDemVorhandenenKoennenBegehbar", testJederRaumIstMitDemVorhandenenKoennenBegehbar),
        ("testSpielstandUeberlebtEinenSpeicherdurchlauf", testSpielstandUeberlebtEinenSpeicherdurchlauf)
    ]
}

fileprivate extension SimulationTests {
    @available(*, deprecated, message: "Not actually deprecated. Marked as deprecated to allow inclusion of deprecated tests (which test deprecated functionality) without warnings")
    static nonisolated(unsafe) let __allTests__SimulationTests = [
        ("testAllePartiturenLaden", testAllePartiturenLaden),
        ("testDauerlaufWechseltDenRaum", testDauerlaufWechseltDenRaum),
        ("testDirigentPlantNotenInDerZeitFolge", testDirigentPlantNotenInDerZeitFolge),
        ("testFernkampfKostetResonanzUndErzeugtGeschosse", testFernkampfKostetResonanzUndErzeugtGeschosse),
        ("testFigurFaelltAufDenBodenUndBleibtImRaum", testFigurFaelltAufDenBodenUndBleibtImRaum),
        ("testIntensitaetSteigtInGefahr", testIntensitaetSteigtInGefahr),
        ("testJedeRegionsmusikExistiert", testJedeRegionsmusikExistiert),
        ("testLeiseSpurenSchweigenBeiGeringerIntensitaet", testLeiseSpurenSchweigenBeiGeringerIntensitaet),
        ("testMusikWechseltMitDerRegion", testMusikWechseltMitDerRegion),
        ("testNahkampfFuelltDieResonanzWiederAuf", testNahkampfFuelltDieResonanzWiederAuf),
        ("testOhneResonanzKeinFernkampf", testOhneResonanzKeinFernkampf),
        ("testSpielStartetImErstenRaum", testSpielStartetImErstenRaum),
        ("testZufaelligeEingabenBringenDasSpielNichtAusDemTritt", testZufaelligeEingabenBringenDasSpielNichtAusDemTritt)
    ]
}

fileprivate extension WorldTests {
    @available(*, deprecated, message: "Not actually deprecated. Marked as deprecated to allow inclusion of deprecated tests (which test deprecated functionality) without warnings")
    static nonisolated(unsafe) let __allTests__WorldTests = [
        ("testAlleRaeumeLaden", testAlleRaeumeLaden),
        ("testJedeFaehigkeitLiegtGenauEinmalInDerWelt", testJedeFaehigkeitLiegtGenauEinmalInDerWelt),
        ("testRaeumeSindVonFelsUmschlossen", testRaeumeSindVonFelsUmschlossen),
        ("testSpawnpunkteStehenImFreien", testSpawnpunkteStehenImFreien),
        ("testTuerenSindGegenseitigVerbunden", testTuerenSindGegenseitigVerbunden)
    ]
}
@available(*, deprecated, message: "Not actually deprecated. Marked as deprecated to allow inclusion of deprecated tests (which test deprecated functionality) without warnings")
func __ResonanzCoreTests__allTests() -> [XCTestCaseEntry] {
    return [
        testCase(PhysicsTests.__allTests__PhysicsTests),
        testCase(ProgressionTests.__allTests__ProgressionTests),
        testCase(SimulationTests.__allTests__SimulationTests),
        testCase(WorldTests.__allTests__WorldTests)
    ]
}