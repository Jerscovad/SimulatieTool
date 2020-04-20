% Ewtsp.m
% programma om uurwaarden voor energieproductie door windturbines en 
% zonnepanelen op te slaan in:
% A. in een mat-file
% B. in een Excel-file
% 
% Arie Taal 
% The Hague University of Applied Sciences (THUAS)
% Department of mechanical Engineering
% April 5th 2019

% Esolarpanel: opgewekte elektriciteit door de zonnepanelen % MWh
% Ewindturbine: opgewekte elektriciteit door de windturbines % MWh
% Esolarpanel: Vermogen zonnepanelen % kW
% Ewindturbine: Vermogen windturbines % kW

clear x y
Ewt=round(Ewindturbine(:,2)*100)/100; % Eerste kolom is de tijd
Pwt=round(Pwindturbine(:,2)*100)/100;
Esp=round(Esolarpanel(:,2)*100)/100; % Twee decimalen
Psp=round(Psolarpanel(:,2)*100)/100;
time=Esolarpanel(:,1);

save Ewtzp time Ewt Pwt Esp Esp % Opslag in Ewtzp.mat

prompt='Wil je de resultaten opslaan in Excel(0=nee /1=ja)? ';
opslaan=input(prompt);
if opslaan==1
prompt='Geef de Excelbestandsnaam: ';
name=input(prompt,'s');
text={'time [hr]' ; 'time [s]'; 'Ewindturbines[MWh]'; 'Pwindturbines [kW]'; 'Esolarpanels [MWh]'; 'Psolarpanels [kW]'};
text=text';
E(:,1)=[1:8761];
E(:,2)=time;
E(:,3)=Ewt;
E(:,4)=Pwt;
E(:,5)=Esp;
E(:,6)=Psp;

xlswrite(strcat(name,' Energy generation'),text,'Energy','A1:F6');
xlswrite(strcat(name,' Energy generation'),E,'Energy','A2:F8762');

end