# Simulatietool

Deze Simulatie tool is gemaakt om aan de hand van gegeven weerdata en zonnepaneel/windtubrine configuraties het vermogen en energie te berekenen (simuleren).

_____

## Inhoudsopgave
1. [Vooraf](https://github.com/Jerscovad/SimulatieTool#vooraf)
2. [Installatie](https://github.com/Jerscovad/SimulatieTool#installatie)
3. [Gebruiks Handleiding](https://github.com.Jerscovad/SimulatieTool#gebruiks-handleiding)
4. [De Grafische User Interface (GUI)](https://github.com/Jerscovad/SimulatieTool#de-grafische-user-interface-gui)
5. [De Simulatie functie](https://github.com/Jerscovad/SimulatieTool#de-simulatie-functie)
   * [De attributen](https://github.com/Jerscovad/SimulatieTool#de-attributen)
   * [De functies](https://github.com/Jerscovad/SimulatieTool#de-functies)
   * [calc_solar functie](https://github.com/Jerscovad/SimulatieTool#calc_solar-functie)
   * [calc_wind functie](https://github.com/Jerscovad/SimulatieTool#calc_wind-functie)
   * [calc_toal functie](https://github.com/Jerscovad/SimulatieTool#calc_total-functie)
6. [De Train functie](https://github.com/Jerscovad/SimulatieTool#de-train-functie)
 
_____

## Vooraf
Deze tool is volledig geschreven in [Python](https://www.python.org/) (support vanaf versie 3.6) en maakt onder andere gebruik van de [numpy](https://numpy.org/), [pandas](https://pandas.pydata.org/), [wxPython](https://wxpython.org/), [matplotlib](https://matplotlib.org/) libraries. Andere libraries die worden gebruikt zullen indien nodig worden toegelicht. De calculaties/berekeningen die worden gedaan zijn gebaseerd op matlab en simulink [scripts en simulaties](https://github.com/Jerscovad/SimulatieTool/tree/master/Matlab).

De simulatietool bestaat uit twee delen/functies. Een Simulatie functie en een Train functie elke met hun eigen tabje in het tooltje. De Train functie is een wat uitgebreidere functie die door middel van een genetisch algoritme (GA) de optimale uikomst probeert te bereiken.
Om het geheel overzichtelijk en makkelijk in gebruik te maken is het ondergebracht in een GUI oftwel Grafische User Interface.

_____

## Installatie 
_____

## Gebruiks Handleiding

De handleiding van de simtool kun je [hier](https://github.com/Jerscovad/SimulatieTool/raw/master/documents/Handleiding%20simtool.pdf "Instruction manual download") downloaden. De handleiding is ook te zien op [deze](https://github.com/Jerscovad/SimulatieTool/blob/master/documents/Handleiding%20simtool.pdf "Instruction manual page") pagina.
_____

## De Grafische User Interface (GUI)
De GUI is gemaakt met behulp van de [wxPython](https://wxpython.org/) en [matplotlib](https://matplotlib.org/) libraries. Dit heeft als voordeel dat de GUI op meerdere besturingssystemen ondersteuning heeft.

De huidige versie heeft een eenvoudig globaal ontwerp zoals hieronder te zien is.
![GUI layout](https://github.com/Jerscovad/SimulatieTool/blob/master/images/design/GUI_classes.png)

Voor meer informatie over de GUI en hoe die werkt raadpleeg het kopje [Gebruiks Handleiding](https://github.com/Jerscovad/SimulatieTool#gebruiks-handleiding)

_____

## De Simulatie functie

De Simulatie functie is de basis waarop de tool is gebouwd. Het is ondergebracht in zijn eigen [klasse](https://github.com/Jerscovad/SimulatieTool/blob/master/src/simulator.py) met functies. In de onderstaande diagram is te zien hoe de klasse is opgebouwd.
![Simulator class](https://github.com/Jerscovad/SimulatieTool/blob/master/images/design/Simulator_class.png)

Voor het simuleren met data afkomsten van Schiphol over het jaar 2016 wordt het Simulatie object als volgt geinitialiseerd:
```python
Sim_schiphol = Simulator(Location('schiphol'),'2016', Windturbine('3MW'))
```

In de [__init__](https://github.com/Jerscovad/SimulatieTool/blob/master/src/simulator.py#L22) functie is te zien dat er meer parameters kunnen worden meegegeven maar deze zijn als [default parameter](https://docs.python.org/2.0/ref/function.html) gedefinieerd. Dit betekend dat ze indien ze onveranderd blijven, niet ingevuld hoeven te worden. Bij de initialisatie wordt ook meteen de windturbine meegegeven. Dit is nodig om de juiste curve te gebruiken voor de windturbine. Meer over de windturbines en curves [hier]().

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
- **dni:** Direkte neerwaardse straling. Gebruikt bij de zonne vermogen/energie berekening. Komt uit de import data.
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

De functie berkend het vermogen en de energie voor de zonnepanelen en 'returned' deze in twee aparte [numpy arrays](https://numpy.org/doc/stable/reference/generated/numpy.array.html?highlight=array#numpy.array). De grootte van deze arrays is afhankelijk van de weerdata die als input wordt meegegeven. Meer over de weerdata [hier]().


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

Als de `sp_eff` en `gref` niet worden aangepast kan het bovenstaande, aangezien ze [default parameter](https://docs.python.org/2.0/ref/function.html) zijn, als volgt worden geschreven:

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

_____

## De Train functie
De train functie maakt gebruik van de Simulatie functie in combinatie met een gentisch algoritme(GA) om de optimale configuratie te vinden. Ter ondersteuning hiervan wordt ook een kosten calculator gebruikt.
Dit is allemaal ondergebracht in een Trainer klasse.

Onderstaande diagram geeft deels aan hoe de Train functie te werk gaat.
![training sequence](https://github.com/Jerscovad/SimulatieTool/blob/master/images/design/Train_sequence.png)


```python
trainer = Trainer(parent, generations, group_size, n_configs, surface_min, 
                 surface_max, angle_min, angle_max, orientation_min, 
                 orientation_max, sp_eff, mutation_percentage, turbines_min, turbines_max, 
                 turbine_height, turbine_type, solar_price, storage_price, demand, 
                 shortage_price, turbine_price, surplus_price, train_by_price,
                 location, year, latitude, longitude, terrain_factor)
```
Korte omschrijving van de parameters:
- **generations:** Hoeveelheid generaties van het GA. Een generatie bevat meerdere groepen.
- **group_size:** Grootte van iedere generatie van het GA. Een groep bevat meedere configuraties.
- **n_configs:** Hoeveel zonnepaneel configuraties er moeten zijn. Dit kan 1 tot 4 zijn.
- **surface_min/surface_max:** Minimale/maximale oppervlakte die het GA mag gebruiken.
- **angle_min/angle_min:** Minimale/maximale hoek ([Inc](https://github.com/Jerscovad/SimulatieTool#calc_solar-functie)) dat het GA mag gebruiken
- **orientation_min/orientation_max:** Minimale/maximale ([Az](https://github.com/Jerscovad/SimulatieTool#calc_solar-functie)) orientatie dat het GA mag gebruiken.
- **sp_eff:** Efficientie van de zonnepanelen.
- **mutationPercentage:** Percentage van verschil tussen iedere configuratie in een generatie.
- **turbines_min/turbines_max:** Minimale/maximale aantal windturbines dat het GA mag gebruiken.
- **turbine_height:** Hoogte van de rotor as van de windturbine.
- **turbine_type:** Het type van de windturbine.
- **solar_price:** Prijs van de zonnepanelen in €/m<sup>2</sup>.
- **storage_price:** Prijs van de opslag in €/kWh.
- **demand:** De constante vraag van vermogen in kW.
- **shortage_price:** Prijs van onderproductie €/kWh.
- **turbine_price:** Prijs van de windturbine in €/kW.
- **surplus_price:** Prijs van overproductie in €/kWh.
- **train_by_price:** Moet het algoritme trainen volgens de kosten of volgens vermogen en energie.
- **location:** Locatie waar de weerdata van afkomstig moet zijn.
- **year:** Jaar waarin de weerdata is opgenomen.
- **latitude:** Coördinaat van de locatie waar het om gaat. Wordt uit het Locatie object uitgelezen tenzij een waarde wordt ingevoerd.
- **longitude:** Coördinaat van de locatie waar het om gaat. Wordt uit het Locatie object uitgelezen tenzij een waarde wordt ingevoerd.
- **terrain_factor:** Terreingesteldheidsfactor die wordt gebruikt bij wind vermogen/energie berekening. Wordt uit het locatie object uitgelezen tenzij een waarde wordt ingevoerd.

Met het Trainer object kan nu worden getrained door de `train` functie aan te roepen zoals in [deze](https://github.com/Jerscovad/SimulatieTool/blob/master/images/design/Train_sequence.png) afbeelding te zien is. Wanneer de training klaar is wordt de beste cofiguratie gereturned.

_____

## De Weerdata

De weerdata is afkomstig uit KNMI data en is aangepast om gebruikt te kunnen worden in de simulatie functie. Daarnaast zijn uit de KNMI data ook nieuwe gegevens berekend die nodig zijn in de simulatie functie.
Voor iedere locatie is per jaar de data verdeeld in verschillende `csv` bestanden.
In ieder bestand zitten 8760 rijen met daarin:
- Datum
- Uur van de dag
- Windsnelheid
- Temperatuur (wordt momenteel niet gebruikt)
- Q oftewel de GHI (Globale Horizontale Straling)
- Luchtdruk (wordt momenteel niet gebruikt)
- DNI (Direkte Neerwaartse Straling)

Deze gegevens worden uit het bestand gelezen wanneer er een Simulator object wordt aangemaakt.

_____

## Windturbines

_____
