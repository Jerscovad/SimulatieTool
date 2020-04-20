# Simulatietool

Deze Simulatie tool is gemaakt om aan de hand van gegeven weerdata en zonnepaneel/windtubrine configuraties het vermogen en energie te berekenen (simuleren).

_____

## Inhoudsopgave
1. [Vooraf](https://github.com/Jerscovad/SimulatieTool#vooraf)
2. [De Simulatie functie](https://github.com/Jerscovad/SimulatieTool#de-simulatie-functie)
   * [De attributen](https://github.com/Jerscovad/SimulatieTool#de-attributen)
   * [De functies](https://github.com/Jerscovad/SimulatieTool#de-functies)
   * [calc_solar functie](https://github.com/Jerscovad/SimulatieTool#calc_solar-functie)
   * [calc_wind functie](https://github.com/Jerscovad/SimulatieTool#calc_wind-functie)
   * [calc_toal functie](https://github.com/Jerscovad/SimulatieTool#calc_total-functie)
3. [De Train functie](https://github.com/Jerscovad/SimulatieTool#de-train-functie)
4. [De Grafische User Interface (GUI)](https://github.com/Jerscovad/SimulatieTool#de-grafische-user-interface-gui)
5. [Installatie Handleiding](https://github.com/Jerscovad/SimulatieTool#installatie-handleiding)
6. [Gebruiks Handleiding](https://github.com.Jerscovad/SimulatieTool#gebruiks-handleiding)

## Vooraf
Deze tool is volledig geschreven in [Python](https://www.python.org/) (support vanaf versie 3.6) en maakt onder andere gebruik van de [numpy](https://numpy.org/), [pandas](https://pandas.pydata.org/), [wxPython](https://wxpython.org/), [matplotlib](https://matplotlib.org/) libraries. Andere libraries die worden gebruikt zullen indien nodig worden toegelicht. De calculaties/berekeningen die worden gedaan zijn gebaseerd op matlab en simulink [scripts en simulaties](https://github.com/Jerscovad/SimulatieTool/tree/master/Matlab).

De simulatietool bestaat uit twee delen/functies. Een Simulatie functie en een Train functie elke met hun eigen tabje in het tooltje. De Train functie is een wat uitgebreidere functie die door middel van een genetisch algoritme (GA) de optimale uikomst probeert te bereiken.
De gehele tool is in Python geschreven.

_____

## De Simulatie functie

De Simulatie functie is de basis waarop de tool is gebouwd. Het is ondergebracht in zijn eigen [klasse](https://github.com/Jerscovad/SimulatieTool/blob/master/src/simulator.py) met functies. In de onderstaande diagram is te zien hoe de klasse is opgebouwd.
![Simulator class](https://github.com/Jerscovad/SimulatieTool/blob/master/images/design/Simulator_classe.png)

Voor het simuleren met data afkomsten van Schiphol over het jaar 2016 wordt het Simulatie object als volgt geinitialiseerd:
```python
Sim_schiphol = Simulator(Location('schiphol'),'2016', Windturbine(5))
```

In de [__init__](https://github.com/Jerscovad/SimulatieTool/blob/master/src/simulator.py#L22) functie is te zien dat er meer parameters kunnen worden meegegeven maar deze zijn als [default parameter](https://docs.python.org/2.0/ref/function.html) gedefinieerd dus hoeft het in dit geval niet meegegeven te worden.

### De attributen
De atributen zijn variabelen die nodig zijn ter ondersteuning van de functies. Deze worden ingevoerd door de gebruiker of worden uit een data bestand uitgelezen.
Korte omschrijving van ieder atribuut:
- **Location:** Locatie object dat verschillende locatie specifieke informatie bevat. Zie [Location klasse](https://github.com/Jerscovad/SimulatieTool/blob/master/src/location.py "Location object")
- **year:** Het jaar waar de weer data op is gebasseerd. Wordt ingevoerd.
- **latitude:** Coördinaat van de locatie waar het om gaat. Wordt uit het Locatie object uitgelezen tenzij een waarde wordt ingevoerd.
- **longitude:** idem latitude.
- **terrain_factor:** terreingesteldheidsfactor die wordt gebruikt bij wind vermoge/energie berekening. Wordt uit het locatie object uitgelezen tenzij een waarde wordt ingevoerd.
- **Windturbine:** Windturbine object die informatie over de windturbine bevat. Zie [Windturbine klasse](https://github.com/Jerscovad/SimulatieTool/blob/master/src/generators.py)
- **import_data:** bevat alle geimporteerde weerdata nodig voor de berekeningen. De data wordt bij initialisatie uitgelezen.
- **ghi:** Globale horizontale straling. Gebruikt bij de zonne vermogen/energie berekening. Komt uit de import data.
- **dni:** Direkte neerwaardse straling. Gebruikt bij de zonne vermoge/energie berekening. Komt uit de import data.
- **dates:** Datum informatie die bij de weerdata hoort. Komt uit de import data.
- **doy:** Day of year. Gebruikt bij de zonne vermoge/energie berekening. Wordt gehaald uit de dates variabele.
- **time:** Uur van de dag. Gebruikt bij de zonne vermoge/energie berekening. Komt uit de import data.
- **wind_speed:** Gemeten windsnelheid gebruikt voor de wind vermoge/energie berekening. Komt uit de import data.
- **temperature:** Gemeten temperatuur. Komt uit de import data. Wordt voor nu niet gebruikt.

### De functies
De Simulatie klasse bevat drie functies.
- [calc_solar](https://github.com/Jerscovad/SimulatieTool#calc_solar-functie)
- [calc_wind](https://github.com/Jerscovad/SimulatieTool#calc_wind-functie)
- [calc_total](https://github.com/Jerscovad/SimulatieTool#calc_total-functie)

#### calc_solar functie
Deze functie berekend het vermogen en de energie van zonnepanelen aan de hand van ingevoerde variabelen.
Naast de bovengenoemde ondersteunende attributen heeft deze functie ook nodig: 

* Az(Azimuth): De oriëntatie van de zonnepanelen in graden.
  * Zuid = 0
  * West = 90
  * Oost = -90
  * Noord = 180
* Inc (Inclination): De hoek van de zonnepanelen in graden.
* sp_area: De oppervlakte van de zonnepanelen in vierkante meter.
* sp_eff(efficiency): De efficiëntie van de zonnepanelen in procenten.
* gref: ...Wordt in de berekening wel gebruikt maar is altijd 0...

De functie berkend het vermogen en de energie voor de zonnepanelen en 'returned' deze in twee aparte [numpy arrays](https://numpy.org/doc/stable/reference/generated/numpy.array.html?highlight=array#numpy.array). De grootte van deze arrays is afhankelijk van de weerdata die als input wordt meegegeven.

Momenteel kan de functie alleen worden uitgevoerd met vier opstellingen. Bij minder dan vier kan 0 worden meegegeven als input van de resterende opstellingen.

Stel je wilt dus het vermogen(power) en energie(energy) van de volgende opstellingen:
 * 100m met een hoek van 50 graden naar het zuiden gericht.
 * 200m met een hoek van 45 graden naar het oosten gericht.
 * 300m met een hoek van 30 graden naar het westen gericht.
 * 400m met een hoek van 25 graden naar het zuid-westen gericht.

Onderstaande code zet dan de som van de vier opstellingen in de `power` en `energy` variabelen.
```python
power,energy = Sim_schiphol.calc_solar(Az=[0, -90, 90, 45],Inc=[50, 45, 30, 25],
                                     sp_area=[100, 200, 300, 400],sp_eff=16,gref=0)
```
Aangezien de `sp_eff` en `gref` altijd 16 en 0 respectievelijk zijn, zijn ze als [default parameter](https://docs.python.org/2.0/ref/function.html) gedefiniëerd en kan bovenstaande ook als volgt worden geschreven:

```python
power,energy = Sim_schiphol.calc_solar(Az=[0, -90, 90, 45],Inc=[50, 45, 30, 25],sp_area=[100, 200, 300, 400])
```

#### calc_wind functie
Deze functie berekend het vermogen en de energie van zonnepanelen aan de hand van ingevoerde variabelen.
De functie heeft als input nodig:
* n_turbines: De hoeveelheid windturbines in de configuratie.
* rotor_height: De hoogte van de rotor as

Stel je wilt het vermogen van vijf windturbines met een rotor as hoogte van 100m berkenen.
Onderstaande code zet de som van de vijf turbine vermogens en energie in de `power` en `energy` variabelen.
```python
power,energy = Sim_schiphol.calc_wind([5, 100])
```

#### calc_total functie
Deze functie voert de `calc_solar` en `calc_wind` functies uit en telt de uitkomsten bij elkaar op.

Combinatie van de twee bovenstaande zou worden:
```python
total_power,total_energy = Sim_schiphol.calc_total([100, 50, 0, 200, 45, -90, 300, 30, 90, 400, 25, 45],[5, 100], 16)
```

De grootte van de numpy arrays (power en energy) die uit de functies afkomstig zijn, is afhankelijk van de grootte van de input data. De huidige input data is geformatteerd op een jaar uitgezet in uren dus iedere output zal 8760 data punten bevatten.


_____

## De Train functie


_____

## De Grafische User Interface (GUI)

_____

## Installatie Handleiding

_____

## Gebruiks Handleiding

_____

