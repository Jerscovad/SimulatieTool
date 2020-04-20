%% *irrad_SET calculates irradiation on a tilted surface for PV panels and
%%  solar collectors.*
% Calculates solar irradiation on a tilted surface (like a solar PV-cel)
% using Perez 1990 model using Global horizontal Irradiation and Direct
% normal irradiation. Maxwells DISC model or Perez' DIRINT model can be 
% used to calculate DNI from GHI if this data is not avialable.
%
% Syntax:  SOL=irrad_SET(doy,hour,GHI,DNI,gamma,beta,gref)
%
% Input:
% (scalar or vector) doy    = day of the year (1-365)    
% (scalar or vector) hour   = hour of day (0 - 24)            [hour]
% (scalar or vector) GHI    = Global Horizontal Irradiation   [W/m^2]
% (scalar or vector) DNI    = Direct Normal Irradiation       [W/m^2] 
% (scalar or vector) gamma  = azimuth angle of the surface,   [deg]
%               east:gamma = -90,     west:gamma = 90
%               south:gamma = 0,    north:gamma = 180
% (scalar or vector) beta  = inclination angle of the surface,[deg] 
%               horizontal: beta=0, vertical: beta=90
% (scalair) gref = ground reflection (0-1)
% Output: 
% DTI   = diffuse solar irradiation on a tilted surface       [W/m^2]
% DSTI  = direct solar irradiation on a tilted surface        [W/m^2]
% Rg    = ground reflected irradiation on a tilted surface    [W/m^2]
% GTI   = total solar irradiation on a tilted surface         [W/m^2]
% 
% Default geographical position: Rotterdam Airport, the Netherlands
%
% Sources: 
% [1] R.Perez 1990. "Modelling daylight availability and irradiance components
% from direct and global irradiance", Solar Energy volume 40. 
% In the code "Perez(1)" is refering to formula 1 in this article
% [2] Daryl R. Myers. "Solar Radiation, Practical modeling for renewable 
% energy applications", 2013. 
% In the code "f6.4" is refering to formula 6.4 in this book. Nomenclature
% for variables in this model is taken from this book.
% 
% Coded by: 
% J.A. de Groot, The Hague University of Applied Science, Delft NL 2017
% Adaption by A.C.Taal (ground reflection as input parameter)

function SOL=IrradPV(doy,hour,GHI,DNI,gamma,beta,gref)
global a b F1 F2 cai 
%% location inputs
LST = hour;
nr= length(hour); %for pre-allocation of various vectors
% Rotterdam airport
L=51.95;    % L   = Latitude                     [deg] 
LON=4.45;   % LON = Local Longitude              [deg]  east is positive
LSM=15;     % LSM = Local Standard time Meridian [deg]  east is positive
%gref=0.2;  % gref = ground albedo
r=pi/180;   % for conversion to radians

%% calculation of sun positions                         
d=2*pi*(doy-1)/365;                     % day angle [deg]       f1.1b
decl=23.442.*sind((360/365).*(doy+284)); % declination [deg]     f1.4                              
% equation of time 
EQT = 229.18*(0.0000075+0.001868*cosd(d)-0.032077*sind(d)...
    -0.014615*cosd(2*d)-0.040849*sind(2*d));%                     f1.5 
% hour angle [deg] 
h=15*((LON-LSM)*4/60+(LST-12-0.5+EQT/60));%                     f1.7/1.8  
% hai=sin(solar elevation angle) = cos(solar zenith angle) [deg]
hai=sind(L).*sind(decl)+cosd(L).*cosd(decl).*cosd(h);%          f1.9 

%% calculating DHI from GHI and DNI
DHI = GHI-DNI.*hai;% Diffuse Horizontal Irradiance
DHI(DHI<0)=0;
sel =asind(hai);   % sel=solar elevation angle [deg]
Zen =acosd(hai)*r; % Zen=solar zenith angle [radians!!]

%% Perez factors for calculation of circumsolar and horizon brightness coefficients
    f11=[-0.008 0.130 0.330 0.568 0.873 1.132 1.060 0.678].'; 
    f12=[0.588 0.683 0.487 0.187 -0.392 -1.237 -1.600 -0.327].';
    f13=[-0.062 -0.151 -0.221 -0.295 -0.362 -0.412 -0.3590 -0.2500].';
    f21=[-0.0600 -0.0190 0.0550 0.1090 0.2260 0.2880 0.2640 0.1560].';
    f22=[0.072 0.066 -0.064 -0.152 -0.462 -0.823 -1.1270 -1.3770].';
    f23=[-0.022 -0.029 -0.026 -0.014 0.001 0.056 0.131 0.2510].';

%% determination of bin with eps 
    bin = ones(nr,1); % bin 1 is overcast sky , bin 8 is clear sky
    k =  1.041; % kappa for calculation in radians
    eps= ((DHI+DNI)./DHI+k*Zen.^3)./(1+k*Zen.^3); % Perez(1) (Myers' f6.13 uses degrees)
    bin((eps>=1.065) & (eps<1.23)) = 2;
    bin((eps>=1.23) & (eps<1.5)) = 3;
    bin((eps>=1.5) & (eps<1.95)) = 4;
    bin((eps>=1.95) & (eps<2.8)) = 5;
    bin((eps>=2.8) & (eps<4.5)) = 6;
    bin((eps>=4.5) & (eps<6.2)) = 7;
    bin(eps>=6.2) = 8;

%% calculation of relative air mass
    M=1./hai;
    M(sel<2)=20; % if the sun is below horizon, airmass is set to approximate sunset values
    
%% calculation of extraterrestrial radiation
    Io=1366.1; % solar constant [w/m^2]
    ETR=Io*(1+0.033*cosd(2*pi.*doy)/365); %[deg]
    % delta is "the new sky brightness parameter"
    Delta=DHI.*M./ETR; % Perez(2) 
    
%%  determination of the "new circumsolar brightness coefficient" (F1) 
%   and "horizon brightness coefficient" (F2)
    F1 =f11(bin)+Delta.*f12(bin)+Zen.*f13(bin); %f6.21
    F1(F1<0)=0;
    F2=f21(bin)+Delta.*f22(bin)+Zen.*f23(bin); % f6.22
    
%% determination of cos angle of incidence of tilted surface 
%  cai= cos angle of incidence of Solar to surface = cos(teta)
    cai=sind(decl)*sind(L)*cosd(beta)...
        -sind(decl)*cosd(L)*(sind(beta).*cosd(gamma))...
        +(cosd(decl).*cosd(h))*cosd(L)*cosd(beta)...
        +(cosd(decl).*cosd(h))*sind(L)*(sind(beta).*cosd(gamma))...
         +cosd(decl).*sind(h)*(sind(beta).*sind(gamma)); % [deg]   f1.12  ;
%     cai=sind(decl)*sind(L)*cosd(beta)...
%         -sind(decl)*cosd(L)*sind(beta)*cosd(gamma)...
%         +cosd(decl).*cosd(h)*cosd(L)*cosd(beta)...
%         +cosd(decl).*cosd(h)*sind(L)*sind(beta)*cosd(gamma)...
% %         +cosd(decl).*sind(h)*sind(beta)*sind(gamma); % [deg]   f1.12  
    % decl = decl sun, 
    % phi = lattitude
    % h = omega = hour angle of sun 
    % beta = s = incl angle surface 
    % gamma = azimuth of surface, 
        
 %% determination of the diffuse radiation on a tilted surface DTI, Perez 1990
    a = cai;
    a(a<0)=0;
    b = cos(Zen); % [rad]
    b(b<0.087)=0.087;
    for h=1:4
    c(:,h)=a(:,(h))./b(:).*F1(:);
    end
   
    DTI = DHI.*(1-F1)*(1+cosd(beta))./2 + c + F2*sind(beta); %Perez(9) (Myers' f6.12 is different)
    DTI(DTI<0)=0;

%% direct solar radiation on an tilted surface
for h=1:4
    DSTI(:,h)=cai(:,(h)).*DNI(:);
    end
    %DSTI=cai*DNI;
    DSTI(DSTI<0)=0;

%% the ground reflected component: assume isotropic ground conditions.
    Rg=0.5*gref*(DHI+DNI)*(1-cos(beta)); % f6.4, f6.5, f6.6

%% total irradiation on a tilted surface GTI
    GTI=DTI+DSTI+Rg;

SOL=GTI;
end