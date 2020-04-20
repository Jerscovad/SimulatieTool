% Programma om XLS bestand uit NEN 5060 om te zetten in een MAT bestand.
% Er wordt een matrix uitgevoerd met in de rijen de tijd
% in kolom 2 de windsnelheid op 10 m hoogte

[NUM,TXT,RAW]=xlsread('NEN5060-B2.xls',3);   

t=((1:8760)'-1)*3600;
% dom=NUM(:,3); % day of month
% hod=NUM(:,4); % hour of day
% qglob_hor=NUM(:,5);
% qdiff_hor=NUM(:,6);
% qdir_hor=NUM(:,7);
% qdir_nor=NUM(:,8);
% Toutdoor=NUM(:,9)/10;
% phioutdoor=NUM(:,10);
% xoutdoor=NUM(:,11)/10;
% pdamp=NUM(:,12);
vwind=NUM(:,13)/10; % op 10 m hoogte
% dirwind=NUM(:,14);
% cloud=NUM(:,15)/10;
% rain=NUM(:,16)/10;

% doy=ceil(t/(3600*24)+0.0001);
vwind=horzcat(t,vwind);

save vwind vwind
clear NUM RAW TXT t
