# Simulatietool

Deze tool is gemaakt om te simuleren (berekenen) wat voor vermogen en energie gepaard gaat met gegeven weersgegevens(data).

## In het kort
De simulatietool bestaad uit twee delen/functies. Een Simulatie functie en een Train functie elke met hun eigen tabje in het tooltje. De Train functie is een wat uitgebreidere functie die door middel van een genetisch algoritme (GA) de optimale uikomst probeert te bereiken.
De gehele tool is in Python geschreven.

_____

## Inhoudsopgave
1. [De Simulatie functie](https://github.com/Jerscovad/SimulatieTool#de-simulatie-functie "De Simulatie functie")

## De Simulatie functie

De Simulatie functie is de basis waarop de tool is gebouwd. Het is ondergracht in zijn eigen klasse met functies. In de onderstaande diagram is te zien hoe de klasse is opgebouwd.

### De attributen
De atributen zijn variabelen die nodig zijn ter ondersteuning van de functies. Deze worden ingevoerd door de gebruiker of worden uit een data bestand uitgelezen.
Korte omschrijving van ieder atribuut:
- Location: Locatie object dat verschillende locatie specifieke informatie bevat. Zie [Location object](https://link-voor-bestand. "Location object")
- year: Het jaar waar de weer data op is gebasseerd. Wordt ingevoerd.
- latitude: Coördinaat van de locatie waar het om gaat. Wordt uit het Locatie object uitgelezen tenzij een waarde wordt ingevoerd.
- longitude: idem latitude.
- terrain_factor: terreingesteldheidsfactor die wordt gebruikt bij wind vermoge/energie berekening. Wordt uit het locatie object uitgelezen tenzij een waarde wordt ingevoerd.
- Windturbine: Windturbine object die informatie over de windturbine bevat.
- import_data: bevat alle geimporteerde weerdata nodig voor de berekeningen. De data wordt bij initialisatie uitgelezen.
- ghi: Globale horizontale straling. Gebruikt bij de zonne vermogen/energie berekening. Komt uit de import data.
- dni: Direkte neerwaardse straling. Gebruikt bij de zonne vermoge/energie berekening. Komt uit de import data.
- dates: Datum informatie die bij de weerdata hoort. Komt uit de import data.
- doy: Day of year. Gebruikt bij de zonne vermoge/energie berekening. Wordt gehaald uit de dates variabele.
- time: Uur van de dag. Gebruikt bij de zonne vermoge/energie berekening. Komt uit de import data.
- wind_speed: Gemeten windsnelheid gebruikt voor de wind vermoge/energie berekening. Komt uit de import data.
- temperature: Gemeten temperatuur. Komt uit de import data. Wordt voor nu niet gebruikt.

### De functies
De Simulatie klasse bevat drie functies.
- calc_solar
- calc_wind
- calc_total

### calc_solar
Deze functie berekend het vermogen en de energie van zonnepanelen aande hand van ingevoerde variabelen.
Naast de bovengenoemde ondersteunende attributen heeft deze functie ook nodig: 

- Az(Azimuth): De orientatie van de zonnepanelen in graden.
- Inc (Inclination): De hoek van de zonnepanelen in graden.
- sp_area: De oppervlakte van de zonnepanelen in vierkante meter.
- sp_eff(efficiency): De efficiëntie van de zonnepanelen in procenten.
- gref: ...Wordt in de berekening wel gebruikt maar is altijd 0...

De functie berkend het vermogen en de energie voor de zonnepanelen en 'returned' deze in twee aparte variabelen. Dit kan momenteel alleen met vier opstellingen per keer.

Stel je wilt dus het vermogen(power) en energie(energy) van de volgende opstellingen:
100m met een hoek van 50 graden naar het zuiden gericht.
200m met een hoek van 45 graden naar het oosten gericht.
300m met een hoek van 30 graden naar het westen gericht.
400m met een hoek van 25 graden naar het zuid-westen gericht.

Onderstaande code zet dan de som van de vier opstellingen in de `power` en `energy` variabelen.
```python
power, energy = Simulator.calc_solar(Az=[0, -90, 90, 45], Inc=[50, 45, 30, 25], sp_area=[100, 200, 300, 400], sp_eff=16, gref=0)
```
Aangezien de `sp_eff` en `gref` altijd 16 en 0 zijn, zijn ze als default argument gedefiniëerd dus kan bovenstaande ook als volgt worden geschreven:

```python
power, energy = Simulator.calc_solar(Az=[0, -90, 90, 45], Inc=[50, 45, 30, 25], sp_area=[100, 200, 300, 400])
```

### calc_wind

_____

## De Train functie

_____

## De Grafische User Interface (GUI)

_____

