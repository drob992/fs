import time
import redis
import json
import sys
sys.path.insert(0, '../')
import util
from config import *
import common
import datetime

limit_keys = ['HTH', 'HTHA', 'HTHB', 'HTHC', 'HTHD', 'HTHE', 'HTHF', 'HTHG', 'HTHH', 'HTHI', 'HTHJ', 'HTHK', 'HTHL', 'HTHM', 'HTHN', 'HTHO', 'HTHP', 'HTHQ', 'HTHR', 'HTHS', 'HTHT', 'HTHU', 'HTHV', 'HTHW', 'HTHX', 'HTHY', 'HTHZ', 'HTH1', 'HTHA1', 'HTHB1', 'HTHC1', 'HTHD1', 'HTHE1', 'HTHF1', 'HTHG1', 'HTHH1', 'HTHI1', 'HTHJ1', 'HTHK1', 'HTHL1', 'HTHM1', 'HTHN1', 'HTHO1', 'HTHP1', 'HTHQ1', 'HTHR1', 'HTHS1', 'HTHT1', 'HTHU1', 'HTHV1', 'HTHW1', 'HTHX1', 'HTHY1', 'HTHZ1', 'HTHX', 'HTHAX', 'HTHBX', 'HTHCX', 'HTHDX', 'HTHEX', 'HTHFX', 'HTHGX', 'HTHHX', 'HTHIX', 'HTHJX', 'HTHKX', 'HTHLX', 'HTHMX', 'HTHNX', 'HTHOX', 'HTHPX', 'HTHQX', 'HTHRX', 'HTHSX', 'HTHTX', 'HTHUX', 'HTHVX', 'HTHWX', 'HTHXX', 'HTHYX', 'HTHZX', 'HTH2', 'HTHA2', 'HTHB2', 'HTHC2', 'HTHD2', 'HTHE2', 'HTHF2', 'HTHG2', 'HTHH2', 'HTHI2', 'HTHJ2', 'HTHK2', 'HTHL2', 'HTHM2', 'HTHN2', 'HTHO2', 'HTHP2', 'HTHQ2', 'HTHR2', 'HTHS2', 'HTHT2', 'HTHU2', 'HTHV2', 'HTHW2', 'HTHX2', 'HTHY2', 'HTHZ2', 'H', 'HA', 'HB', 'HC', 'HD', 'HE', 'HF', 'HG', 'HH', 'HI', 'HJ', 'HK', 'HL', 'HM', 'HN', 'HO', 'HP', 'HQ', 'HR', 'HS', 'HT', 'HU', 'HV', 'HW', 'HX', 'HY', 'HZ', 'H1', 'HA1', 'HB1', 'HC1', 'HD1', 'HE1', 'HF1', 'HG1', 'HH1', 'HI1', 'HJ1', 'HK1', 'HL1', 'HM1', 'HN1', 'HO1', 'HP1', 'HQ1', 'HR1', 'HS1', 'HT1', 'HU1', 'HV1', 'HW1', 'HX1', 'HY1', 'HZ1', 'HX', 'HAX', 'HBX', 'HCX', 'HDX', 'HEX', 'HFX', 'HGX', 'HHX', 'HIX', 'HJX', 'HKX', 'HLX', 'HMX', 'HNX', 'HOX', 'HPX', 'HQX', 'HRX', 'HSX', 'HTX', 'HUX', 'HVX', 'HWX', 'HXX', 'HYX', 'HZX', 'H2', 'HA2', 'HB2', 'HC2', 'HD2', 'HE2', 'HF2', 'HG2', 'HH2', 'HI2', 'HJ2', 'HK2', 'HL2', 'HM2', 'HN2', 'HO2', 'HP2', 'HQ2', 'HR2', 'HS2', 'HT2', 'HU2', 'HV2', 'HW2', 'HX2', 'HY2', 'HZ2', 'LFT', 'LFTA', 'LFTB', 'LFTC', 'LFTD', 'LFTE', 'LFTF', 'LFTG', 'LFTH', 'LFTI', 'LFTJ', 'LFTK', 'LFTL', 'LFTM', 'LFTN', 'LFTO', 'LFTP', 'LFTQ', 'LFTR', 'LFTS', 'LFTT', 'LFTU', 'LFTV', 'LFTW', 'LFTX', 'LFTY', 'LFTZ', 'MTFT', 'MTFTA', 'MTFTB', 'MTFTC', 'MTFTD', 'MTFTE', 'MTFTF', 'MTFTG', 'MTFTH', 'MTFTI', 'MTFTJ', 'MTFTK', 'MTFTL', 'MTFTM', 'MTFTN', 'MTFTO', 'MTFTP', 'MTFTQ', 'MTFTR', 'MTFTS', 'MTFTT', 'MTFTU', 'MTFTV', 'MTFTW', 'MTFTX', 'MTFTY', 'MTFTZ', 'LTFT', 'LTFTA', 'LTFTB', 'LTFTC', 'LTFTD', 'LTFTE', 'LTFTF', 'LTFTG', 'LTFTH', 'LTFTI', 'LTFTJ', 'LTFTK', 'LTFTL', 'LTFTM', 'LTFTN', 'LTFTO', 'LTFTP', 'LTFTQ', 'LTFTR', 'LTFTS', 'LTFTT', 'LTFTU', 'LTFTV', 'LTFTW', 'LTFTX', 'LTFTY', 'LTFTZ', 'LHT', 'LHTA', 'LHTB', 'LHTC', 'LHTD', 'LHTE', 'LHTF', 'LHTG', 'LHTH', 'LHTI', 'LHTJ', 'LHTK', 'LHTL', 'LHTM', 'LHTN', 'LHTO', 'LHTP', 'LHTQ', 'LHTR', 'LHTS', 'LHTT', 'LHTU', 'LHTV', 'LHTW', 'LHTX', 'LHTY', 'LHTZ', 'MTHT', 'MTHTA', 'MTHTB', 'MTHTC', 'MTHTD', 'MTHTE', 'MTHTF', 'MTHTG', 'MTHTH', 'MTHTI', 'MTHTJ', 'MTHTK', 'MTHTL', 'MTHTM', 'MTHTN', 'MTHTO', 'MTHTP', 'MTHTQ', 'MTHTR', 'MTHTS', 'MTHTT', 'MTHTU', 'MTHTV', 'MTHTW', 'MTHTX', 'MTHTY', 'MTHTZ', 'LTHT', 'LTHTA', 'LTHTB', 'LTHTC', 'LTHTD', 'LTHTE', 'LTHTF', 'LTHTG', 'LTHTH', 'LTHTI', 'LTHTJ', 'LTHTK', 'LTHTL', 'LTHTM', 'LTHTN', 'LTHTO', 'LTHTP', 'LTHTQ', 'LTHTR', 'LTHTS', 'LTHTT', 'LTHTU', 'LTHTV', 'LTHTW', 'LTHTX', 'LTHTY', 'LTHTZ', 'CN', 'CNA', 'CNB', 'CNC', 'CND', 'CNE', 'CNF', 'CNG', 'CNH', 'CNI', 'CNJ', 'CNK', 'CNL', 'CNM', 'CNN', 'CNO', 'CNP', 'CNQ', 'CNR', 'CNS', 'CNT', 'CNU', 'CNV', 'CNW', 'CNX', 'CNY', 'CNZ', 'CN_LT', 'CN_LTA', 'CN_LTB', 'CN_LTC', 'CN_LTD', 'CN_LTE', 'CN_LTF', 'CN_LTG', 'CN_LTH', 'CN_LTI', 'CN_LTJ', 'CN_LTK', 'CN_LTL', 'CN_LTM', 'CN_LTN', 'CN_LTO', 'CN_LTP', 'CN_LTQ', 'CN_LTR', 'CN_LTS', 'CN_LTT', 'CN_LTU', 'CN_LTV', 'CN_LTW', 'CN_LTX', 'CN_LTY', 'CN_LTZ', 'CN_GT', 'CN_GTA', 'CN_GTB', 'CN_GTC', 'CN_GTD', 'CN_GTE', 'CN_GTF', 'CN_GTG', 'CN_GTH', 'CN_GTI', 'CN_GTJ', 'CN_GTK', 'CN_GTL', 'CN_GTM', 'CN_GTN', 'CN_GTO', 'CN_GTP', 'CN_GTQ', 'CN_GTR', 'CN_GTS', 'CN_GTT', 'CN_GTU', 'CN_GTV', 'CN_GTW', 'CN_GTX', 'CN_GTY', 'CN_GTZ', 'CN_EX', 'CN_EXA', 'CN_EXB', 'CN_EXC', 'CN_EXD', 'CN_EXE', 'CN_EXF', 'CN_EXG', 'CN_EXH', 'CN_EXI', 'CN_EXJ', 'CN_EXK', 'CN_EXL', 'CN_EXM', 'CN_EXN', 'CN_EXO', 'CN_EXP', 'CN_EXQ', 'CN_EXR', 'CN_EXS', 'CN_EXT', 'CN_EXU', 'CN_EXV', 'CN_EXW', 'CN_EXX', 'CN_EXY', 'CN_EXZ', 'ACNHT', 'ACNHTA', 'ACNHTB', 'ACNHTC', 'ACNHTD', 'ACNHTE', 'ACNHTF', 'ACNHTG', 'ACNHTH', 'ACNHTI', 'ACNHTJ', 'ACNHTK', 'ACNHTL', 'ACNHTM', 'ACNHTN', 'ACNHTO', 'ACNHTP', 'ACNHTQ', 'ACNHTR', 'ACNHTS', 'ACNHTT', 'ACNHTU', 'ACNHTV', 'ACNHTW', 'ACNHTX', 'ACNHTY', 'ACNHTZ', 'ACNHT_LT', 'ACNHT_LTA', 'ACNHT_LTB', 'ACNHT_LTC', 'ACNHT_LTD', 'ACNHT_LTE', 'ACNHT_LTF', 'ACNHT_LTG', 'ACNHT_LTH', 'ACNHT_LTI', 'ACNHT_LTJ', 'ACNHT_LTK', 'ACNHT_LTL', 'ACNHT_LTM', 'ACNHT_LTN', 'ACNHT_LTO', 'ACNHT_LTP', 'ACNHT_LTQ', 'ACNHT_LTR', 'ACNHT_LTS', 'ACNHT_LTT', 'ACNHT_LTU', 'ACNHT_LTV', 'ACNHT_LTW', 'ACNHT_LTX', 'ACNHT_LTY', 'ACNHT_LTZ', 'ACNHT_GT', 'ACNHT_GTA', 'ACNHT_GTB', 'ACNHT_GTC', 'ACNHT_GTD', 'ACNHT_GTE', 'ACNHT_GTF', 'ACNHT_GTG', 'ACNHT_GTH', 'ACNHT_GTI', 'ACNHT_GTJ', 'ACNHT_GTK', 'ACNHT_GTL', 'ACNHT_GTM', 'ACNHT_GTN', 'ACNHT_GTO', 'ACNHT_GTP', 'ACNHT_GTQ', 'ACNHT_GTR', 'ACNHT_GTS', 'ACNHT_GTT', 'ACNHT_GTU', 'ACNHT_GTV', 'ACNHT_GTW', 'ACNHT_GTX', 'ACNHT_GTY', 'ACNHT_GTZ', 'ACSHT_', 'ACSHT_A', 'ACSHT_B', 'ACSHT_C', 'ACSHT_D', 'ACSHT_E', 'ACSHT_F', 'ACSHT_G', 'ACSHT_H', 'ACSHT_I', 'ACSHT_J', 'ACSHT_K', 'ACSHT_L', 'ACSHT_M', 'ACSHT_N', 'ACSHT_O', 'ACSHT_P', 'ACSHT_Q', 'ACSHT_R', 'ACSHT_S', 'ACSHT_T', 'ACSHT_U', 'ACSHT_V', 'ACSHT_W', 'ACSHT_X', 'ACSHT_Y', 'ACSHT_Z', 'ACN', 'ACNA', 'ACNB', 'ACNC', 'ACND', 'ACNE', 'ACNF', 'ACNG', 'ACNH', 'ACNI', 'ACNJ', 'ACNK', 'ACNL', 'ACNM', 'ACNN', 'ACNO', 'ACNP', 'ACNQ', 'ACNR', 'ACNS', 'ACNT', 'ACNU', 'ACNV', 'ACNW', 'ACNX', 'ACNY', 'ACNZ', 'ACN_LT', 'ACN_LTA', 'ACN_LTB', 'ACN_LTC', 'ACN_LTD', 'ACN_LTE', 'ACN_LTF', 'ACN_LTG', 'ACN_LTH', 'ACN_LTI', 'ACN_LTJ', 'ACN_LTK', 'ACN_LTL', 'ACN_LTM', 'ACN_LTN', 'ACN_LTO', 'ACN_LTP', 'ACN_LTQ', 'ACN_LTR', 'ACN_LTS', 'ACN_LTT', 'ACN_LTU', 'ACN_LTV', 'ACN_LTW', 'ACN_LTX', 'ACN_LTY', 'ACN_LTZ', 'ACN_GT', 'ACN_GTA', 'ACN_GTB', 'ACN_GTC', 'ACN_GTD', 'ACN_GTE', 'ACN_GTF', 'ACN_GTG', 'ACN_GTH', 'ACN_GTI', 'ACN_GTJ', 'ACN_GTK', 'ACN_GTL', 'ACN_GTM', 'ACN_GTN', 'ACN_GTO', 'ACN_GTP', 'ACN_GTQ', 'ACN_GTR', 'ACN_GTS', 'ACN_GTT', 'ACN_GTU', 'ACN_GTV', 'ACN_GTW', 'ACN_GTX', 'ACN_GTY', 'ACN_GTZ', 'ACS', 'ACSA', 'ACSB', 'ACSC', 'ACSD', 'ACSE', 'ACSF', 'ACSG', 'ACSH', 'ACSI', 'ACSJ', 'ACSK', 'ACSL', 'ACSM', 'ACSN', 'ACSO', 'ACSP', 'ACSQ', 'ACSR', 'ACSS', 'ACST', 'ACSU', 'ACSV', 'ACSW', 'ACSX', 'ACSY', 'ACSZ', '3WH', '3WHA', '3WHB', '3WHC', '3WHD', '3WHE', '3WHF', '3WHG', '3WHH', '3WHI', '3WHJ', '3WHK', '3WHL', '3WHM', '3WHN', '3WHO', '3WHP', '3WHQ', '3WHR', '3WHS', '3WHT', '3WHU', '3WHV', '3WHW', '3WHX', '3WHY', '3WHZ', '3WH1', '3WH1A', '3WH1B', '3WH1C', '3WH1D', '3WH1E', '3WH1F', '3WH1G', '3WH1H', '3WH1I', '3WH1J', '3WH1K', '3WH1L', '3WH1M', '3WH1N', '3WH1O', '3WH1P', '3WH1Q', '3WH1R', '3WH1S', '3WH1T', '3WH1U', '3WH1V', '3WH1W', '3WH1X', '3WH1Y', '3WH1Z', '3WHX', '3WHXA', '3WHXB', '3WHXC', '3WHXD', '3WHXE', '3WHXF', '3WHXG', '3WHXH', '3WHXI', '3WHXJ', '3WHXK', '3WHXL', '3WHXM', '3WHXN', '3WHXO', '3WHXP', '3WHXQ', '3WHXR', '3WHXS', '3WHXT', '3WHXU', '3WHXV', '3WHXW', '3WHXX', '3WHXY', '3WHXZ', '3WH2', '3WH2A', '3WH2B', '3WH2C', '3WH2D', '3WH2E', '3WH2F', '3WH2G', '3WH2H', '3WH2I', '3WH2J', '3WH2K', '3WH2L', '3WH2M', '3WH2N', '3WH2O', '3WH2P', '3WH2Q', '3WH2R', '3WH2S', '3WH2T', '3WH2U', '3WH2V', '3WH2W', '3WH2X', '3WH2Y', '3WH2Z', '3WH_1HT', '3WH_1HTA', '3WH_1HTB', '3WH_1HTC', '3WH_1HTD', '3WH_1HTE', '3WH_1HTF', '3WH_1HTG', '3WH_1HTH', '3WH_1HTI', '3WH_1HTJ', '3WH_1HTK', '3WH_1HTL', '3WH_1HTM', '3WH_1HTN', '3WH_1HTO', '3WH_1HTP', '3WH_1HTQ', '3WH_1HTR', '3WH_1HTS', '3WH_1HTT', '3WH_1HTU', '3WH_1HTV', '3WH_1HTW', '3WH_1HTX', '3WH_1HTY', '3WH_1HTZ', '3WH_1HT1', '3WH_1HT1A', '3WH_1HT1B', '3WH_1HT1C', '3WH_1HT1D', '3WH_1HT1E', '3WH_1HT1F', '3WH_1HT1G', '3WH_1HT1H', '3WH_1HT1I', '3WH_1HT1J', '3WH_1HT1K', '3WH_1HT1L', '3WH_1HT1M', '3WH_1HT1N', '3WH_1HT1O', '3WH_1HT1P', '3WH_1HT1Q', '3WH_1HT1R', '3WH_1HT1S', '3WH_1HT1T', '3WH_1HT1U', '3WH_1HT1V', '3WH_1HT1W', '3WH_1HT1X', '3WH_1HT1Y', '3WH_1HT1Z', '3WH_1HTX', '3WH_1HTXA', '3WH_1HTXB', '3WH_1HTXC', '3WH_1HTXD', '3WH_1HTXE', '3WH_1HTXF', '3WH_1HTXG', '3WH_1HTXH', '3WH_1HTXI', '3WH_1HTXJ', '3WH_1HTXK', '3WH_1HTXL', '3WH_1HTXM', '3WH_1HTXN', '3WH_1HTXO', '3WH_1HTXP', '3WH_1HTXQ', '3WH_1HTXR', '3WH_1HTXS', '3WH_1HTXT', '3WH_1HTXU', '3WH_1HTXV', '3WH_1HTXW', '3WH_1HTXX', '3WH_1HTXY', '3WH_1HTXZ', '3WH_1HT2', '3WH_1HT2A', '3WH_1HT2B', '3WH_1HT2C', '3WH_1HT2D', '3WH_1HT2E', '3WH_1HT2F', '3WH_1HT2G', '3WH_1HT2H', '3WH_1HT2I', '3WH_1HT2J', '3WH_1HT2K', '3WH_1HT2L', '3WH_1HT2M', '3WH_1HT2N', '3WH_1HT2O', '3WH_1HT2P', '3WH_1HT2Q', '3WH_1HT2R', '3WH_1HT2S', '3WH_1HT2T', '3WH_1HT2U', '3WH_1HT2V', '3WH_1HT2W', '3WH_1HT2X', '3WH_1HT2Y', '3WH_1HT2Z', 'LFT_T1', 'LFT_T1A', 'LFT_T1B', 'LFT_T1C', 'LFT_T1D', 'LFT_T1E', 'LFT_T1F', 'LFT_T1G', 'LFT_T1H', 'LFT_T1I', 'LFT_T1J', 'LFT_T1K', 'LFT_T1L', 'LFT_T1M', 'LFT_T1N', 'LFT_T1O', 'LFT_T1P', 'LFT_T1Q', 'LFT_T1R', 'LFT_T1S', 'LFT_T1T', 'LFT_T1U', 'LFT_T1V', 'LFT_T1W', 'LFT_T1X', 'LFT_T1Y', 'LFT_T1Z', 'T1_MTFT', 'T1_MTFTA', 'T1_MTFTB', 'T1_MTFTC', 'T1_MTFTD', 'T1_MTFTE', 'T1_MTFTF', 'T1_MTFTG', 'T1_MTFTH', 'T1_MTFTI', 'T1_MTFTJ', 'T1_MTFTK', 'T1_MTFTL', 'T1_MTFTM', 'T1_MTFTN', 'T1_MTFTO', 'T1_MTFTP', 'T1_MTFTQ', 'T1_MTFTR', 'T1_MTFTS', 'T1_MTFTT', 'T1_MTFTU', 'T1_MTFTV', 'T1_MTFTW', 'T1_MTFTX', 'T1_MTFTY', 'T1_MTFTZ', 'T1_LTFT', 'T1_LTFTA', 'T1_LTFTB', 'T1_LTFTC', 'T1_LTFTD', 'T1_LTFTE', 'T1_LTFTF', 'T1_LTFTG', 'T1_LTFTH', 'T1_LTFTI', 'T1_LTFTJ', 'T1_LTFTK', 'T1_LTFTL', 'T1_LTFTM', 'T1_LTFTN', 'T1_LTFTO', 'T1_LTFTP', 'T1_LTFTQ', 'T1_LTFTR', 'T1_LTFTS', 'T1_LTFTT', 'T1_LTFTU', 'T1_LTFTV', 'T1_LTFTW', 'T1_LTFTX', 'T1_LTFTY', 'T1_LTFTZ', 'T2_LFT', 'T2_LFTA', 'T2_LFTB', 'T2_LFTC', 'T2_LFTD', 'T2_LFTE', 'T2_LFTF', 'T2_LFTG', 'T2_LFTH', 'T2_LFTI', 'T2_LFTJ', 'T2_LFTK', 'T2_LFTL', 'T2_LFTM', 'T2_LFTN', 'T2_LFTO', 'T2_LFTP', 'T2_LFTQ', 'T2_LFTR', 'T2_LFTS', 'T2_LFTT', 'T2_LFTU', 'T2_LFTV', 'T2_LFTW', 'T2_LFTX', 'T2_LFTY', 'T2_LFTZ', 'T2_MTFT', 'T2_MTFTA', 'T2_MTFTB', 'T2_MTFTC', 'T2_MTFTD', 'T2_MTFTE', 'T2_MTFTF', 'T2_MTFTG', 'T2_MTFTH', 'T2_MTFTI', 'T2_MTFTJ', 'T2_MTFTK', 'T2_MTFTL', 'T2_MTFTM', 'T2_MTFTN', 'T2_MTFTO', 'T2_MTFTP', 'T2_MTFTQ', 'T2_MTFTR', 'T2_MTFTS', 'T2_MTFTT', 'T2_MTFTU', 'T2_MTFTV', 'T2_MTFTW', 'T2_MTFTX', 'T2_MTFTY', 'T2_MTFTZ', 'T2_LTFT', 'T2_LTFTA', 'T2_LTFTB', 'T2_LTFTC', 'T2_LTFTD', 'T2_LTFTE', 'T2_LTFTF', 'T2_LTFTG', 'T2_LTFTH', 'T2_LTFTI', 'T2_LTFTJ', 'T2_LTFTK', 'T2_LTFTL', 'T2_LTFTM', 'T2_LTFTN', 'T2_LTFTO', 'T2_LTFTP', 'T2_LTFTQ', 'T2_LTFTR', 'T2_LTFTS', 'T2_LTFTT', 'T2_LTFTU', 'T2_LTFTV', 'T2_LTFTW', 'T2_LTFTX', 'T2_LTFTY', 'T2_LTFTZ', '_2WCN_FT', '_2WCN_FTA', '_2WCN_FTB', '_2WCN_FTC', '_2WCN_FTD', '_2WCN_FTE', '_2WCN_FTF', '_2WCN_FTG', '_2WCN_FTH', '_2WCN_FTI', '_2WCN_FTJ', '_2WCN_FTK', '_2WCN_FTL', '_2WCN_FTM', '_2WCN_FTN', '_2WCN_FTO', '_2WCN_FTP', '_2WCN_FTQ', '_2WCN_FTR', '_2WCN_FTS', '_2WCN_FTT', '_2WCN_FTU', '_2WCN_FTV', '_2WCN_FTW', '_2WCN_FTX', '_2WCN_FTY', '_2WCN_FTZ', '2WCN_MTFT', '2WCN_MTFTA', '2WCN_MTFTB', '2WCN_MTFTC', '2WCN_MTFTD', '2WCN_MTFTE', '2WCN_MTFTF', '2WCN_MTFTG', '2WCN_MTFTH', '2WCN_MTFTI', '2WCN_MTFTJ', '2WCN_MTFTK', '2WCN_MTFTL', '2WCN_MTFTM', '2WCN_MTFTN', '2WCN_MTFTO', '2WCN_MTFTP', '2WCN_MTFTQ', '2WCN_MTFTR', '2WCN_MTFTS', '2WCN_MTFTT', '2WCN_MTFTU', '2WCN_MTFTV', '2WCN_MTFTW', '2WCN_MTFTX', '2WCN_MTFTY', '2WCN_MTFTZ', '2WCN_LTFT', '2WCN_LTFTA', '2WCN_LTFTB', '2WCN_LTFTC', '2WCN_LTFTD', '2WCN_LTFTE', '2WCN_LTFTF', '2WCN_LTFTG', '2WCN_LTFTH', '2WCN_LTFTI', '2WCN_LTFTJ', '2WCN_LTFTK', '2WCN_LTFTL', '2WCN_LTFTM', '2WCN_LTFTN', '2WCN_LTFTO', '2WCN_LTFTP', '2WCN_LTFTQ', '2WCN_LTFTR', '2WCN_LTFTS', '2WCN_LTFTT', '2WCN_LTFTU', '2WCN_LTFTV', '2WCN_LTFTW', '2WCN_LTFTX', '2WCN_LTFTY', '2WCN_LTFTZ', 'CN_HT', 'CN_HTA', 'CN_HTB', 'CN_HTC', 'CN_HTD', 'CN_HTE', 'CN_HTF', 'CN_HTG', 'CN_HTH', 'CN_HTI', 'CN_HTJ', 'CN_HTK', 'CN_HTL', 'CN_HTM', 'CN_HTN', 'CN_HTO', 'CN_HTP', 'CN_HTQ', 'CN_HTR', 'CN_HTS', 'CN_HTT', 'CN_HTU', 'CN_HTV', 'CN_HTW', 'CN_HTX', 'CN_HTY', 'CN_HTZ', 'CN_MTHT', 'CN_MTHTA', 'CN_MTHTB', 'CN_MTHTC', 'CN_MTHTD', 'CN_MTHTE', 'CN_MTHTF', 'CN_MTHTG', 'CN_MTHTH', 'CN_MTHTI', 'CN_MTHTJ', 'CN_MTHTK', 'CN_MTHTL', 'CN_MTHTM', 'CN_MTHTN', 'CN_MTHTO', 'CN_MTHTP', 'CN_MTHTQ', 'CN_MTHTR', 'CN_MTHTS', 'CN_MTHTT', 'CN_MTHTU', 'CN_MTHTV', 'CN_MTHTW', 'CN_MTHTX', 'CN_MTHTY', 'CN_MTHTZ', 'CN_LTHT', 'CN_LTHTA', 'CN_LTHTB', 'CN_LTHTC', 'CN_LTHTD', 'CN_LTHTE', 'CN_LTHTF', 'CN_LTHTG', 'CN_LTHTH', 'CN_LTHTI', 'CN_LTHTJ', 'CN_LTHTK', 'CN_LTHTL', 'CN_LTHTM', 'CN_LTHTN', 'CN_LTHTO', 'CN_LTHTP', 'CN_LTHTQ', 'CN_LTHTR', 'CN_LTHTS', 'CN_LTHTT', 'CN_LTHTU', 'CN_LTHTV', 'CN_LTHTW', 'CN_LTHTX', 'CN_LTHTY', 'CN_LTHTZ', 'EXCN_HT', 'EXCN_HTA', 'EXCN_HTB', 'EXCN_HTC', 'EXCN_HTD', 'EXCN_HTE', 'EXCN_HTF', 'EXCN_HTG', 'EXCN_HTH', 'EXCN_HTI', 'EXCN_HTJ', 'EXCN_HTK', 'EXCN_HTL', 'EXCN_HTM', 'EXCN_HTN', 'EXCN_HTO', 'EXCN_HTP', 'EXCN_HTQ', 'EXCN_HTR', 'EXCN_HTS', 'EXCN_HTT', 'EXCN_HTU', 'EXCN_HTV', 'EXCN_HTW', 'EXCN_HTX', 'EXCN_HTY', 'EXCN_HTZ', 'AH', 'AHA', 'AHB', 'AHC', 'AHD', 'AHE', 'AHF', 'AHG', 'AHH', 'AHI', 'AHJ', 'AHK', 'AHL', 'AHM', 'AHN', 'AHO', 'AHP', 'AHQ', 'AHR', 'AHS', 'AHT', 'AHU', 'AHV', 'AHW', 'AHX', 'AHY', 'AHZ', 'AH1', 'AH1A', 'AH1B', 'AH1C', 'AH1D', 'AH1E', 'AH1F', 'AH1G', 'AH1H', 'AH1I', 'AH1J', 'AH1K', 'AH1L', 'AH1M', 'AH1N', 'AH1O', 'AH1P', 'AH1Q', 'AH1R', 'AH1S', 'AH1T', 'AH1U', 'AH1V', 'AH1W', 'AH1X', 'AH1Y', 'AH1Z', 'AH2', 'AH2A', 'AH2B', 'AH2C', 'AH2D', 'AH2E', 'AH2F', 'AH2G', 'AH2H', 'AH2I', 'AH2J', 'AH2K', 'AH2L', 'AH2M', 'AH2N', 'AH2O', 'AH2P', 'AH2Q', 'AH2R', 'AH2S', 'AH2T', 'AH2U', 'AH2V', 'AH2W', 'AH2X', 'AH2Y', 'AH2Z', 'AH_HT', 'AH_HTA', 'AH_HTB', 'AH_HTC', 'AH_HTD', 'AH_HTE', 'AH_HTF', 'AH_HTG', 'AH_HTH', 'AH_HTI', 'AH_HTJ', 'AH_HTK', 'AH_HTL', 'AH_HTM', 'AH_HTN', 'AH_HTO', 'AH_HTP', 'AH_HTQ', 'AH_HTR', 'AH_HTS', 'AH_HTT', 'AH_HTU', 'AH_HTV', 'AH_HTW', 'AH_HTX', 'AH_HTY', 'AH_HTZ', 'AH_HT1', 'AH_HT1A', 'AH_HT1B', 'AH_HT1C', 'AH_HT1D', 'AH_HT1E', 'AH_HT1F', 'AH_HT1G', 'AH_HT1H', 'AH_HT1I', 'AH_HT1J', 'AH_HT1K', 'AH_HT1L', 'AH_HT1M', 'AH_HT1N', 'AH_HT1O', 'AH_HT1P', 'AH_HT1Q', 'AH_HT1R', 'AH_HT1S', 'AH_HT1T', 'AH_HT1U', 'AH_HT1V', 'AH_HT1W', 'AH_HT1X', 'AH_HT1Y', 'AH_HT1Z', 'AH_HT2', 'AH_HT2A', 'AH_HT2B', 'AH_HT2C', 'AH_HT2D', 'AH_HT2E', 'AH_HT2F', 'AH_HT2G', 'AH_HT2H', 'AH_HT2I', 'AH_HT2J', 'AH_HT2K', 'AH_HT2L', 'AH_HT2M', 'AH_HT2N', 'AH_HT2O', 'AH_HT2P', 'AH_HT2Q', 'AH_HT2R', 'AH_HT2S', 'AH_HT2T', 'AH_HT2U', 'AH_HT2V', 'AH_HT2W', 'AH_HT2X', 'AH_HT2Y', 'AH_HT2Z', '_2WCN_FT', '_2WCN_FTA', '_2WCN_FTB', '_2WCN_FTC', '_2WCN_FTD', '_2WCN_FTE', '_2WCN_FTF', '_2WCN_FTG', '_2WCN_FTH', '_2WCN_FTI', '_2WCN_FTJ', '_2WCN_FTK', '_2WCN_FTL', '_2WCN_FTM', '_2WCN_FTN', '_2WCN_FTO', '_2WCN_FTP', '_2WCN_FTQ', '_2WCN_FTR', '_2WCN_FTS', '_2WCN_FTT', '_2WCN_FTU', '_2WCN_FTV', '_2WCN_FTW', '_2WCN_FTX', '_2WCN_FTY', '_2WCN_FTZ', '_2WCN_MTFT', '_2WCN_MTFTA', '_2WCN_MTFTB', '_2WCN_MTFTC', '_2WCN_MTFTD', '_2WCN_MTFTE', '_2WCN_MTFTF', '_2WCN_MTFTG', '_2WCN_MTFTH', '_2WCN_MTFTI', '_2WCN_MTFTJ', '_2WCN_MTFTK', '_2WCN_MTFTL', '_2WCN_MTFTM', '_2WCN_MTFTN', '_2WCN_MTFTO', '_2WCN_MTFTP', '_2WCN_MTFTQ', '_2WCN_MTFTR', '_2WCN_MTFTS', '_2WCN_MTFTT', '_2WCN_MTFTU', '_2WCN_MTFTV', '_2WCN_MTFTW', '_2WCN_MTFTX', '_2WCN_MTFTY', '_2WCN_MTFTZ', '_2WCN_LTFT', '_2WCN_LTFTA', '_2WCN_LTFTB', '_2WCN_LTFTC', '_2WCN_LTFTD', '_2WCN_LTFTE', '_2WCN_LTFTF', '_2WCN_LTFTG', '_2WCN_LTFTH', '_2WCN_LTFTI', '_2WCN_LTFTJ', '_2WCN_LTFTK', '_2WCN_LTFTL', '_2WCN_LTFTM', '_2WCN_LTFTN', '_2WCN_LTFTO', '_2WCN_LTFTP', '_2WCN_LTFTQ', '_2WCN_LTFTR', '_2WCN_LTFTS', '_2WCN_LTFTT', '_2WCN_LTFTU', '_2WCN_LTFTV', '_2WCN_LTFTW', '_2WCN_LTFTX', '_2WCN_LTFTY', '_2WCN_LTFTZ', 'ACNHT', 'ACNHTA', 'ACNHTB', 'ACNHTC', 'ACNHTD', 'ACNHTE', 'ACNHTF', 'ACNHTG', 'ACNHTH', 'ACNHTI', 'ACNHTJ', 'ACNHTK', 'ACNHTL', 'ACNHTM', 'ACNHTN', 'ACNHTO', 'ACNHTP', 'ACNHTQ', 'ACNHTR', 'ACNHTS', 'ACNHTT', 'ACNHTU', 'ACNHTV', 'ACNHTW', 'ACNHTX', 'ACNHTY', 'ACNHTZ', 'ACNHT_LT', 'ACNHT_LTA', 'ACNHT_LTB', 'ACNHT_LTC', 'ACNHT_LTD', 'ACNHT_LTE', 'ACNHT_LTF', 'ACNHT_LTG', 'ACNHT_LTH', 'ACNHT_LTI', 'ACNHT_LTJ', 'ACNHT_LTK', 'ACNHT_LTL', 'ACNHT_LTM', 'ACNHT_LTN', 'ACNHT_LTO', 'ACNHT_LTP', 'ACNHT_LTQ', 'ACNHT_LTR', 'ACNHT_LTS', 'ACNHT_LTT', 'ACNHT_LTU', 'ACNHT_LTV', 'ACNHT_LTW', 'ACNHT_LTX', 'ACNHT_LTY', 'ACNHT_LTZ', 'ACNHT_GT', 'ACNHT_GTA', 'ACNHT_GTB', 'ACNHT_GTC', 'ACNHT_GTD', 'ACNHT_GTE', 'ACNHT_GTF', 'ACNHT_GTG', 'ACNHT_GTH', 'ACNHT_GTI', 'ACNHT_GTJ', 'ACNHT_GTK', 'ACNHT_GTL', 'ACNHT_GTM', 'ACNHT_GTN', 'ACNHT_GTO', 'ACNHT_GTP', 'ACNHT_GTQ', 'ACNHT_GTR', 'ACNHT_GTS', 'ACNHT_GTT', 'ACNHT_GTU', 'ACNHT_GTV', 'ACNHT_GTW', 'ACNHT_GTX', 'ACNHT_GTY', 'ACNHT_GTZ', 'ACSHT_', 'ACSHT_A', 'ACSHT_B', 'ACSHT_C', 'ACSHT_D', 'ACSHT_E', 'ACSHT_F', 'ACSHT_G', 'ACSHT_H', 'ACSHT_I', 'ACSHT_J', 'ACSHT_K', 'ACSHT_L', 'ACSHT_M', 'ACSHT_N', 'ACSHT_O', 'ACSHT_P', 'ACSHT_Q', 'ACSHT_R', 'ACSHT_S', 'ACSHT_T', 'ACSHT_U', 'ACSHT_V', 'ACSHT_W', 'ACSHT_X', 'ACSHT_Y', 'ACSHT_Z', 'LTFT_T1', 'LTFT_T1A', 'LTFT_T1B', 'LTFT_T1C', 'LTFT_T1D', 'LTFT_T1E', 'LTFT_T1F', 'LTFT_T1G', 'LTFT_T1H', 'LTFT_T1I', 'LTFT_T1J', 'LTFT_T1K', 'LTFT_T1L', 'LTFT_T1M', 'LTFT_T1N', 'LTFT_T1O', 'LTFT_T1P', 'LTFT_T1Q', 'LTFT_T1R', 'LTFT_T1S', 'LTFT_T1T', 'LTFT_T1U', 'LTFT_T1V', 'LTFT_T1W', 'LTFT_T1X', 'LTFT_T1Y', 'LTFT_T1Z', 'MTFT_T1', 'MTFT_T1A', 'MTFT_T1B', 'MTFT_T1C', 'MTFT_T1D', 'MTFT_T1E', 'MTFT_T1F', 'MTFT_T1G', 'MTFT_T1H', 'MTFT_T1I', 'MTFT_T1J', 'MTFT_T1K', 'MTFT_T1L', 'MTFT_T1M', 'MTFT_T1N', 'MTFT_T1O', 'MTFT_T1P', 'MTFT_T1Q', 'MTFT_T1R', 'MTFT_T1S', 'MTFT_T1T', 'MTFT_T1U', 'MTFT_T1V', 'MTFT_T1W', 'MTFT_T1X', 'MTFT_T1Y', 'MTFT_T1Z', 'LFT_T1', 'LFT_T1A', 'LFT_T1B', 'LFT_T1C', 'LFT_T1D', 'LFT_T1E', 'LFT_T1F', 'LFT_T1G', 'LFT_T1H', 'LFT_T1I', 'LFT_T1J', 'LFT_T1K', 'LFT_T1L', 'LFT_T1M', 'LFT_T1N', 'LFT_T1O', 'LFT_T1P', 'LFT_T1Q', 'LFT_T1R', 'LFT_T1S', 'LFT_T1T', 'LFT_T1U', 'LFT_T1V', 'LFT_T1W', 'LFT_T1X', 'LFT_T1Y', 'LFT_T1Z', 'LTFT_T2', 'LTFT_T2A', 'LTFT_T2B', 'LTFT_T2C', 'LTFT_T2D', 'LTFT_T2E', 'LTFT_T2F', 'LTFT_T2G', 'LTFT_T2H', 'LTFT_T2I', 'LTFT_T2J', 'LTFT_T2K', 'LTFT_T2L', 'LTFT_T2M', 'LTFT_T2N', 'LTFT_T2O', 'LTFT_T2P', 'LTFT_T2Q', 'LTFT_T2R', 'LTFT_T2S', 'LTFT_T2T', 'LTFT_T2U', 'LTFT_T2V', 'LTFT_T2W', 'LTFT_T2X', 'LTFT_T2Y', 'LTFT_T2Z', 'MTFT_T2', 'MTFT_T2A', 'MTFT_T2B', 'MTFT_T2C', 'MTFT_T2D', 'MTFT_T2E', 'MTFT_T2F', 'MTFT_T2G', 'MTFT_T2H', 'MTFT_T2I', 'MTFT_T2J', 'MTFT_T2K', 'MTFT_T2L', 'MTFT_T2M', 'MTFT_T2N', 'MTFT_T2O', 'MTFT_T2P', 'MTFT_T2Q', 'MTFT_T2R', 'MTFT_T2S', 'MTFT_T2T', 'MTFT_T2U', 'MTFT_T2V', 'MTFT_T2W', 'MTFT_T2X', 'MTFT_T2Y', 'MTFT_T2Z', 'LFT_T2', 'LFT_T2A', 'LFT_T2B', 'LFT_T2C', 'LFT_T2D', 'LFT_T2E', 'LFT_T2F', 'LFT_T2G', 'LFT_T2H', 'LFT_T2I', 'LFT_T2J', 'LFT_T2K', 'LFT_T2L', 'LFT_T2M', 'LFT_T2N', 'LFT_T2O', 'LFT_T2P', 'LFT_T2Q', 'LFT_T2R', 'LFT_T2S', 'LFT_T2T', 'LFT_T2U', 'LFT_T2V', 'LFT_T2W', 'LFT_T2X', 'LFT_T2Y', 'LFT_T2Z', 'HTH', 'HTHA', 'HTHB', 'HTHC', 'HTHD', 'HTHE', 'HTHF', 'HTHG', 'HTHH', 'HTHI', 'HTHJ', 'HTHK', 'HTHL', 'HTHM', 'HTHN', 'HTHO', 'HTHP', 'HTHQ', 'HTHR', 'HTHS', 'HTHT', 'HTHU', 'HTHV', 'HTHW', 'HTHX', 'HTHY', 'HTHZ', 'HTH1', 'HTHA1', 'HTHB1', 'HTHC1', 'HTHD1', 'HTHE1', 'HTHF1', 'HTHG1', 'HTHH1', 'HTHI1', 'HTHJ1', 'HTHK1', 'HTHL1', 'HTHM1', 'HTHN1', 'HTHO1', 'HTHP1', 'HTHQ1', 'HTHR1', 'HTHS1', 'HTHT1', 'HTHU1', 'HTHV1', 'HTHW1', 'HTHX1', 'HTHY1', 'HTHZ1', 'HTHX', 'HTHAX', 'HTHBX', 'HTHCX', 'HTHDX', 'HTHEX', 'HTHFX', 'HTHGX', 'HTHHX', 'HTHIX', 'HTHJX', 'HTHKX', 'HTHLX', 'HTHMX', 'HTHNX', 'HTHOX', 'HTHPX', 'HTHQX', 'HTHRX', 'HTHSX', 'HTHTX', 'HTHUX', 'HTHVX', 'HTHWX', 'HTHXX', 'HTHYX', 'HTHZX', 'HTH2', 'HTHA2', 'HTHB2', 'HTHC2', 'HTHD2', 'HTHE2', 'HTHF2', 'HTHG2', 'HTHH2', 'HTHI2', 'HTHJ2', 'HTHK2', 'HTHL2', 'HTHM2', 'HTHN2', 'HTHO2', 'HTHP2', 'HTHQ2', 'HTHR2', 'HTHS2', 'HTHT2', 'HTHU2', 'HTHV2', 'HTHW2', 'HTHX2', 'HTHY2', 'HTHZ2', 'HTH', 'HTHA', 'HTHB', 'HTHC', 'HTHD', 'HTHE', 'HTHF', 'HTHG', 'HTHH', 'HTHI', 'HTHJ', 'HTHK', 'HTHL', 'HTHM', 'HTHN', 'HTHO', 'HTHP', 'HTHQ', 'HTHR', 'HTHS', 'HTHT', 'HTHU', 'HTHV', 'HTHW', 'HTHX', 'HTHY', 'HTHZ', 'HTH1', 'HTHA1', 'HTHB1', 'HTHC1', 'HTHD1', 'HTHE1', 'HTHF1', 'HTHG1', 'HTHH1', 'HTHI1', 'HTHJ1', 'HTHK1', 'HTHL1', 'HTHM1', 'HTHN1', 'HTHO1', 'HTHP1', 'HTHQ1', 'HTHR1', 'HTHS1', 'HTHT1', 'HTHU1', 'HTHV1', 'HTHW1', 'HTHX1', 'HTHY1', 'HTHZ1', 'HTHX', 'HTHAX', 'HTHBX', 'HTHCX', 'HTHDX', 'HTHEX', 'HTHFX', 'HTHGX', 'HTHHX', 'HTHIX', 'HTHJX', 'HTHKX', 'HTHLX', 'HTHMX', 'HTHNX', 'HTHOX', 'HTHPX', 'HTHQX', 'HTHRX', 'HTHSX', 'HTHTX', 'HTHUX', 'HTHVX', 'HTHWX', 'HTHXX', 'HTHYX', 'HTHZX', 'HTH2', 'HTHA2', 'HTHB2', 'HTHC2', 'HTHD2', 'HTHE2', 'HTHF2', 'HTHG2', 'HTHH2', 'HTHI2', 'HTHJ2', 'HTHK2', 'HTHL2', 'HTHM2', 'HTHN2', 'HTHO2', 'HTHP2', 'HTHQ2', 'HTHR2', 'HTHS2', 'HTHT2', 'HTHU2', 'HTHV2', 'HTHW2', 'HTHX2', 'HTHY2', 'HTHZ2', 'H', 'HA', 'HB', 'HC', 'HD', 'HE', 'HF', 'HG', 'HH', 'HI', 'HJ', 'HK', 'HL', 'HM', 'HN', 'HO', 'HP', 'HQ', 'HR', 'HS', 'HT', 'HU', 'HV', 'HW', 'HX', 'HY', 'HZ', 'H1', 'HA1', 'HB1', 'HC1', 'HD1', 'HE1', 'HF1', 'HG1', 'HH1', 'HI1', 'HJ1', 'HK1', 'HL1', 'HM1', 'HN1', 'HO1', 'HP1', 'HQ1', 'HR1', 'HS1', 'HT1', 'HU1', 'HV1', 'HW1', 'HX1', 'HY1', 'HZ1', 'H2', 'HA2', 'HB2', 'HC2', 'HD2', 'HE2', 'HF2', 'HG2', 'HH2', 'HI2', 'HJ2', 'HK2', 'HL2', 'HM2', 'HN2', 'HO2', 'HP2', 'HQ2', 'HR2', 'HS2', 'HT2', 'HU2', 'HV2', 'HW2', 'HX2', 'HY2', 'HZ2', 'LGIM_MD_INFO', 'LGIM_MD_P', 'LGIM_MD_M', 'LFT1', 'LFT2', 'LFT3', 'LFT4', 'LFT5', 'LFT6', 'LFT7', 'LFT8', 'LFT9', 'LFT10', 'MTFT1', 'MTFT2', 'MTFT3', 'MTFT4', 'MTFT5', 'MTFT6', 'MTFT7', 'MTFT8', 'MTFT9', 'MTFT10', 'LTFT1', 'LTFT2', 'LTFT3', 'LTFT4', 'LTFT5', 'LTFT6', 'LTFT7', 'LTFT8', 'LTFT9', 'LTFT10', 'LHT1', 'LHT2', 'LHT3', 'LHT4', 'LHT5', 'LHT6', 'LHT7', 'LHT8', 'LHT9', 'LHT10', 'MTHT1', 'MTHT2', 'MTHT3', 'MTHT4', 'MTHT5', 'MTHT6', 'MTHT7', 'MTHT8', 'MTHT9', 'MTHT10', 'LTHT1', 'LTHT2', 'LTHT3', 'LTHT4', 'LTHT5', 'LTHT6', 'LTHT7', 'LTHT8', 'LTHT9', 'LTHT10', 'LT1', 'LTT1', 'MTT1', 'LT2', 'LTT2', 'MTT2', 'LT1', 'LTT1', 'ET1', 'MTT1', 'LT2', 'LTT2', 'ET2', 'MTT2', 'LQ2TR', 'LTQ2TR', 'MTQ2TR', 'LQ3TR', 'LTQ3TR', 'MTQ3TR', 'LQ4TR', 'LTQ4TR', 'MTQ4TR', 'LSHT', 'LTLSHT', 'MTLSHT', 'LHT', 'LTHT', 'MTHT', 'FQ2TRH', 'FQ2TRH1', 'FQ2TRH2', 'FQ3TRH', 'FQ3TRH1', 'FQ3TRH2', 'FQ4TRH', 'FQ4TRH1', 'FQ4TRH2', 'SHTA', 'SHTA1', 'SHTA2','LGIS_MD_INFO','LGIS_MD_P','LGIS_MD_M','LGIS_MD_INFO1','LGIS_MD_P1','LGIS_MD_M1','LGIS_MD_INFO2','LGIS_MD_P2','LGIS_MD_M2','LGIS_MD_INFO3','LGIS_MD_P3','LGIS_MD_M3','LGIS_MD_INFO4','LGIS_MD_P4','LGIS_MD_M4','LGIS_MD_INFO5','LGIS_MD_P5','LGIS_MD_M5','FQTRH', 'FQTRH1', 'FQTRH2', 'LQTR', 'LTQTR', 'MTQTR', 'LP1TR', 'LTP1TR', 'MTP1TR', 'LP2TR', 'LTP2TR', 'MTP2TR', 'LP3TR', 'LTP3TR', 'MTP3TR', 'SHTHA', 'SHTHA1', 'SHTHA2', 'T1GW', 'T2GW', 'MTT1GW', 'LTT1GW', 'MTT2GW', 'LTT2GW', 'LPIS_MD_INFO', 'LPIS_MD_P', 'LPIS_MD_M', 'PTSH', 'PTSH1', 'PTSH2', 'PTSHX']


# diff
# reset quotas
# limiti u setu svi idu
# svaki poslednji emit za svaki signal cuvati u redisu u novoj listi (samo osnovni podaci)

rdb = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)
diff_logger = util.parserLog('/var/log/sbp/flashscores/diff_logger.log', 'bet356live-single')
err_logger = util.parserLog('/var/log/sbp/flashscores/single_emmiter.log', 'bet356live-single-emmiter')

if __name__ == '__main__':

	print("Emmiter started. - {}".format(datetime.datetime.now().time()))

	old = {}
	old_games_with_limits = {}
	new_hashes = rdb.keys('single_emmit_*')
	for key in new_hashes:
		rdb.delete(key)

	while True:

		old_hashes = list(old.keys())
		new_hashes = rdb.keys('single_emmit_*')
		crunched = {}

		# lupujem kroz sve sto je stiglo na kanal
		for _ in new_hashes:

			reset_quotas = None

			# single event hash
			event_hash = _[13:]

			# single event dictionary
			try:
				new_event = json.loads(rdb.get(_))[event_hash]
				old_event_key = event_hash

				# da li postoji kljuc u listi starih kljuceva
				if old_event_key in old_hashes:
					# print("ima ga, POREDI")

					diff = {}
					min_for_emmit = {}
					old_event = old[old_event_key]

					for key in list(new_event.keys()):
						if key != 'odds':

							min_for_emmit[key] = new_event[key]

							if key not in list(old_event.keys()):
								diff[key] = new_event[key]
							else:
								if old_event[key] != new_event[key]:
									diff[key] = new_event[key]

					if 'odds' in list(new_event.keys()):

						if rdb.smembers(common.redis_channels['flush_data']):
							if event_hash in list(rdb.smembers(common.redis_channels['flush_data'])):
								if 'odds' in list(old[event_hash].keys()):
									reset_quotas = True
									# print("setujem nule za: {}".format(event_hash))
									for odd_key in list(old[event_hash]['odds'].keys()):
										old[event_hash]['odds'][odd_key] = 0

								rdb.srem(common.redis_channels['flush_data'], event_hash)
								# print("posle: {}".format(rdb.smembers(common.redis_channels['flush_data'])))

						if reset_quotas:
							diff['odds'] = old[event_hash]['odds']
							# print("vracam nule")
						else:
							diff['odds'] = {}
							new_odds = new_event['odds']

							if 'odds' in list(old_event.keys()):
								old_odds = old_event['odds']

								for key in new_odds:

									if key in limit_keys:
										if event_hash not in list(old_games_with_limits.keys()):
											old_games_with_limits[event_hash] = {}
										old_games_with_limits[event_hash][key] = new_odds[key]

									if key not in list(old_odds.keys()):
										# print("nema {}".format(key))

										diff['odds'][key] = new_odds[key]
									else:

										if old_odds[key] != new_odds[key]:
											# print("razlikuje se {}".format(key))
											diff['odds'][key] = new_odds[key]
										# else:
										#     print("ne razlikuju se {}".format(key))

								# print("POREDJENJE SA STARIMA")
							else:
								# print("NEMA STARIH KVOTA")
								diff['odds'] = new_odds

						if 'odds' in list(diff.keys()):
							if not len(diff['odds'].keys()):
								del diff['odds']

					if len(list(diff.keys())):
						# print("{}: razlika je u: {}".format(event_hash, list(diff.keys())))
						for key in list(min_for_emmit.keys()):
							diff[key] = min_for_emmit[key]

						crunched[event_hash] = diff
					# else:
					# 	pass
						# print("nema razlike")
				else:
					# jer ne postoji u listi prethodnih saljem ceo emit
					crunched[event_hash] = new_event

				# apdejtujem mapu starih sa novim emitom
				old[old_event_key] = new_event
				if reset_quotas:
					try:
						old[old_event_key]['odds'] = crunched[event_hash]['odds']
					except Exception as e:
						diff_logger.critical('[Emmiter] - {}'.format(e))

			except Exception as err:
				print("err na single emiteru")
				print(err)
				err_logger.critical(err)

		if len(list(crunched.keys())):
			for event_hash in list(crunched.keys()):

				if 'odds' in list(crunched[event_hash].keys()) and event_hash in list(old_games_with_limits.keys()):
					for g_key in crunched[event_hash]['odds']:
						if g_key in limit_keys and g_key in list(old_games_with_limits[event_hash].keys()):
							for l_key in list(old_games_with_limits[event_hash].keys()):
								crunched[event_hash]['odds'][l_key] = old_games_with_limits[event_hash][l_key]
							break

			for h_ in list(endpoint_rdb_ch_sets.keys()):
				# print(crunched, "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
				rdb.lpush(endpoint_rdb_ch_sets[h_]['publish_ch'], json.dumps(crunched))
			diff_logger.info(crunched)

		time.sleep(1)
