
libname input "C:\Users\kkapur\OneDrive - argenx BVBA\Desktop\ARGX-113\ARGX-113-1704\SAScode\seronegative_samplesize\Viyatest";
%let path = C:\Users\kkapur\OneDrive - argenx BVBA\Desktop\ARGX-113\ARGX-113-1704\SAScode\seronegative_samplesize\Viyatest\;
%let path2 = C:\Users\kkapur\OneDrive - argenx BVBA\Desktop\ARGX-113\ARGX-113-1704\SAScode\seronegative_samplesize\Viyatest\;
%let inputd1 = simdata1.xlsx;
%let inputd2 = simdata2.xlsx;
%let outd = modsum.xlsx;
%let outd2 = modOC.xlsx;
%let logt = log.txt;
%let nst1 = 50; 
%let nst2 = 50;
%let nmax = 75;

%let Ntot = %sysfunc(ceil(&nst1+&nst2)); 
%put &Ntot; 

%let iter = 500;  /* Need simulations for 10,000 to 100,000*/
%let seed11i = 1;
%let seed21i = 4;
%let seed12i = 2;
%let seed22i = 3;
%let cp1fut = 0.10;
%let cp1lowpz = 0.30;
%let cp2highpz = 0.90;
%let cst1 = 3.586925; /*Hwang, Shi & DeCani alpha spending gamma = -10*/
%let cst2 = 1.960395;
%let beta = 0.01;

ods listing close;
ods select none;
ods _all_ close;
options nonotes;
ods trace off;
ods exclude all;
ods graphics off;
proc printto log="&path.&logt"; run;


proc import datafile = "&path.&inputd1" DBMS = excel OUT = dbsim1;
run;
proc import datafile = "&path.&inputd2" DBMS = excel OUT = dbsim2;
run;


data dbsim1c(type=corr);
set dbsim1;
run;

data dbsim2c(type=corr);
set dbsim2;
run;

%include "C:\Users\kkapur\OneDrive - argenx BVBA\Desktop\ARGX-113\ARGX-113-1704\SAScode\seronegative_samplesize\Viyatest\simdata.sas";

%simdata(&nst1,dbsim1c,dbsim2c,dat_stg1,&iter,&seed11i,&seed21i);

proc sort data=dat_stg1; by  iterID SID trt t;
run;

ods output LSMEstimates=est1st1a ConvergenceStatus=cs1st1a;
PROC MIXED DATA=dat_stg1;
by iterID;
CLASS SID trt(ref='1') t ;
MODEL chg= trt t trt*t / DDFM=KR S;
REPEATED t /SUBJECT=SID TYPE=AR(1);
lsmestimate t*trt 'W04'
   	0	0	0	1	0	0	0	0	0	 
   	0	0	0	-1	0	0	0	0	0 / divisor=1 e alpha=0.05;
RUN;


data res1a;
merge est1st1a cs1st1a;
by iterID;
run;

data res1a;
set res1a;
if status = 1 then delete;
TotalNst1 = 2*&nst1;
TotalNst2 = 2*&nst2;
TotalN = TotalNst1 + TotalNst2;
TotalNst2max = 2*&nmax;
TotalN2new= TotalNst2;
w1=sqrt(TotalNst1/TotalN);
w2=sqrt(TotalNst2/TotalN);
wratio = w1/w2;
zvalt = quantile('normal',1- Probt/2);
if tValue<0 then zValue = -zvalt;
if tValue>=0 then zValue = zvalt;
CondPow =1-probnorm(&cst2./w2 - zValue*wratio - zValue/wratio);
CondPow2 =1-probnorm(&cst2./w2 - tValue*wratio - tValue/wratio);
zCp = Probit(1-&beta.);
futflag=0;
unfflag=0;
prmflag=0;
favflag=0;
effflag=0;
if CondPow < &cp1fut then do; Region="FUTILE"; futflag = 1; end;
else if &cp1fut =< CondPow =< &cp1lowpz then do; Region="UNFAVO"; unfflag=1; end;
else if &cp1lowpz =< CondPow =< &cp2highpz then do; Region="PROMIS"; prmflag=1; end;
else if (CondPow > &cp2highpz) and (tValue > &cst1) then do; Region="FAVORA"; favflag=1; end;
else if (CondPow > &cp2highpz) and (tValue <= &cst1) then do; Region="EFFICA"; effflag=1; end;
if Region in("PROMIS") then do;
TotalN2new =  TotalNst2max;
end;
N2new = TotalN2new /2;
TotalNfinal = TotalNst1 + TotalN2new;
run;

data res1a;
set res1a;
drop Label DF Probt Alpha Lower Upper Reason Status pdG pdH;
rename Estimate = Diffst1 StdErr= SEst1 tValue=tst1 zvalue=zst1;
run;

data dat_stg2;
iterID = 0;
run;

%macro simdatst2;
%do icnt = 1 %to &iter;
%let n2st2 = 0;
data _null_;
set res1a;
if iterID = &icnt then call symput('n2st2',trim(left(put(N2new,4.))));
run;
%let sed1 = %sysfunc(ceil(&seed12i + 10*&icnt));
%let sed2 = %sysfunc(ceil(&seed22i + 3*&icnt));

%simdata(&nst2,dbsim1c,dbsim2c,dat_stg2iter&icnt,1,&sed1,&sed2);

data dat_stg2iter&icnt;
set dat_stg2iter&icnt;
iterID = &icnt;
run;
data dat_stg2;
set dat_stg2 dat_stg2iter&icnt;
run;
proc delete data = dat_stg2iter&icnt; 
%end;
quit;
%mend;
quit;

%simdatst2;
quit;

data dat_stg2;
set dat_stg2;
if iterID = 0 then delete;
run;

proc sort data=dat_stg2; by  iterID SID trt t;
run;

ods output LSMEstimates=est1st2a ConvergenceStatus=cs1st2a;
PROC MIXED DATA=dat_stg2;
by iterID;
CLASS SID trt(ref='1') t ;
MODEL chg= trt t trt*t / DDFM=KR S;
REPEATED t /SUBJECT=SID TYPE=AR(1);
lsmestimate t*trt 'W04'
   	0	0	0	1	0	0	0	0	0	 
   	0	0	0	-1	0	0	0	0	0 / divisor=1 e alpha=0.05;
RUN;


data res2a;
merge est1st2a cs1st2a;
by iterID;
run;

data res2a;
set res2a;
if status = 1 then delete;
run;

data res2a;
set res2a;
zvalt = quantile('normal',1- Probt/2);
if tValue<0 then zValue = -zvalt;
if tValue>=0 then zValue = zvalt;
drop Label DF Probt Alpha Lower Upper Reason Status pdG pdH;
rename Estimate = Diffst2 StdErr= SEst2 tValue=tst2 zvalue=zst2;
run;

data finalres;
merge res1a res2a;
by iterID;
run;

data finalres;
set finalres;
zCHW = w1*zst1 + w2*zst2;
power = 0;
if zCHW > &cst2 then power = 1;
if Region in("EFFICA") then do;
power =  1;
end;
if Region in("FUTILE") then do;
power =  0;
end;
run;

proc sort data=finalres;
by Region;
run;
proc univariate data=finalres noprint;
by Region;
var TotalNfinal CondPow futflag unfflag prmflag favflag effflag Power;
output out=sumres mean=TotalNfinalavg CondPowavg futflagavg unfflagavg prmflagavg favflagavg effflagavg Poweravg
run;

proc univariate data=finalres noprint;
var TotalNfinal CondPow futflag unfflag prmflag favflag effflag Power;
output out=sumresoverall mean=TotalNfinalavg CondPowavg futflagavg unfflagavg prmflagavg favflagavg effflagavg Poweravg;
run;

data sumresoverall;
set sumresoverall;
Region = "Overall";
run;

data oc;
set sumres sumresoverall;
run;

proc printto;
run;

proc export data = oc DBMS = excel OUTFILE = "&path2.&outd";
run;
quit;

proc export data = finalres DBMS = excel OUTFILE = "&path2.&outd2";
run;
quit;



