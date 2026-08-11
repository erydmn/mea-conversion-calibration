# src/dwsim_harness.py
"""Faz 5: DWSIM Otomasyonu (Pythonnet).

DWSIM flowsheet'i (Flowsheet.dwxmz) ile baglanti kurar,
optimizasyon sonuclarini (X_abs, X_reg) flowsheet'e aktarir
(Reaction.Expression uzerinden), simulasyonu calistirir
ve DWSIM'in gercek sonuclarini (kompresyon isi vb.) okur.

Gereksinimler:
- Windows OS
- DWSIM kurulumu (varsayilan: C:/Users/Public/DWSIM)
- pythonnet (pip install pythonnet)
"""
import os
import sys

def setup_dwsim_environment(dwsim_path="C:/Users/Public/DWSIM"):
    """DWSIM .NET bilesenlerini pythonnet (clr) ile yukler."""
    try:
        import clr
    except ImportError:
        raise ImportError("pythonnet yuklu degil! 'pip install pythonnet' komutunu calistirin.")
        
    if not os.path.exists(dwsim_path):
        raise FileNotFoundError(f"DWSIM yolu bulunamadi: {dwsim_path}")
        
    # DLL Yollarini ekle
    sys.path.append(dwsim_path)
    
    # DWSIM DLL'lerini yukle
    clr.AddReference("DWSIM.Interfaces")
    clr.AddReference("DWSIM.GlobalSettings")
    clr.AddReference("DWSIM.SharedClasses")
    clr.AddReference("DWSIM.Thermodynamics")
    clr.AddReference("DWSIM.UnitOperations")
    clr.AddReference("DWSIM.Inspector")
    clr.AddReference("DWSIM.Automation")
    
    # Gerekli namespacelerden import yap (bunu fonksiyon disina da alabiliriz, ama clr lazim)
    # import DWSIM.Interfaces as DI
    
    # Locale ayari cok onemli! (Turkce Windows'ta virgul/nokta hatasini onler)
    from System.Threading import Thread
    from System.Globalization import CultureInfo
    Thread.CurrentThread.CurrentCulture = CultureInfo.InvariantCulture
    Thread.CurrentThread.CurrentUICulture = CultureInfo.InvariantCulture

class DWSIMHarness:
    """DWSIM Flowsheet yonetim sinifi."""
    
    def __init__(self, flowsheet_path, cfg, dwsim_path="C:/Users/Excalıbur/AppData/Local/DWSIM"):
        self.flowsheet_path = flowsheet_path
        self.cfg = cfg
        self.dwsim_path = dwsim_path
        self.interf = None
        self.flowsheet = None
        
        setup_dwsim_environment(dwsim_path)
        self._load_flowsheet()
        
    def _load_flowsheet(self):
        """Flowsheeti yukler (Automation3)."""
        from DWSIM.Automation import Automation3
        self.interf = Automation3()
        print(f"DWSIM Flowsheet yukleniyor: {self.flowsheet_path}")
        self.flowsheet = self.interf.LoadFlowsheet(self.flowsheet_path)
        
    def set_conversion(self, rxn_name, conversion_fraction):
        """Reaksiyon donusum oranini ayarlar (Reaction.Expression)."""
        # DWSIM icinde reaksiyon objesini bul ve expression'i (Expression) guncelle.
        rxn = self.flowsheet.Reactions[rxn_name]
        # Ornek: 0.906 -> "90.6"
        # Not: Conversion reaksiyonlarinda donusum Expression alaninda yuzde olarak tutulur.
        rxn.Expression = str(round(conversion_fraction * 100, 4))
        
    def calculate(self):
        """Simulasyonu calistirir."""
        from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
        
        # Hesapla
        print("DWSIM hesaplamasi baslatiliyor...")
        error_list = self.interf.CalculateFlowsheet2(self.flowsheet)
        
        if error_list is not None and len(error_list) > 0:
            print("Hesaplama tamamlandi, ancak HATA/UYARI mesajlari var:")
            for err in error_list:
                print(f"  - {err}")
        else:
            print("Hesaplama BASARIYLA tamamlandi.")
            
    def get_stream_property(self, stream_name, property_name):
        """Belirtilen akimin (Stream) ozelligini okur.
        Ornek: Temperature, Pressure, MassFlow, EnergyFlow..."""
        obj_interface = self.flowsheet.GetFlowsheetSimulationObject(stream_name)
        if obj_interface is None:
            return None
        
        try:
            obj = obj_interface.GetAsObject()
            
            if property_name == "MassFlow":
                return float(obj.GetMassFlow()) # kg/s
            elif property_name == "Temperature":
                return float(obj.GetTemperature())
            elif property_name == "Pressure":
                return float(obj.GetPressure())
            elif property_name == "EnergyFlow":
                return float(obj.EnergyFlow) # kW
            else:
                attr_val = getattr(obj, property_name, None)
                if attr_val is not None:
                    return float(attr_val)
        except Exception as e:
            print(f"Dogrudan ozellik okuma hatasi {property_name}: {e}")
            
        return None
        
    def check_mass_balance(self):
        """Temel kutle ve CO2 dengesini kontrol eder."""
        print("\n--- Kutle Dengesi Kontrolu ---")
        try:
            streams = self.cfg['dwsim_map']['streams']
            flue_in = self.get_stream_property(streams['flue_gas_in'], "MassFlow")
            gas_out = self.get_stream_property(streams['clean_gas'], "MassFlow")
            co2_out = self.get_stream_property(streams['co2_product'], "MassFlow")
            
            print(f"  Flue Gas In: {flue_in:.2f} kg/s")
            print(f"  Clean Gas:   {gas_out:.2f} kg/s")
            print(f"  CO2 Product: {co2_out:.2f} kg/s")
            
            # Kaba denge
            fark = flue_in - (gas_out + co2_out)
            print(f"  (Giris - Cikis) Fark: {fark:.4f} kg/s")
        except Exception as e:
            print(f"Kutle dengesi okunamadi: {e}")

    def get_kpis(self):
        """DWSIM'den kompresyon isi, reboiler gorevi (HT-1) gibi ozel metrikleri dondurur."""
        try:
            # Compressor work (if mapped)
            comp_work = 0.0
            if 'units' in self.cfg['dwsim_map'] and 'compressor' in self.cfg['dwsim_map']['units']:
                comp_tag = self.cfg['dwsim_map']['units']['compressor']
                cw = self.get_stream_property(comp_tag, "EnergyFlow")
                if cw is not None: comp_work = cw
                
            # Reboiler duty (HT-1 heater energy stream, e.g. E-03)
            # Defaulting to E-03 based on user feedback
            reboiler_duty = 0.0
            reb_duty_val = self.get_stream_property("E-03", "EnergyFlow")
            if reb_duty_val is not None:
                reboiler_duty = reb_duty_val # kW

            return {
                'compressor_work_kW': comp_work,
                'reboiler_duty_kW': reboiler_duty
            }
        except Exception as e:
            print(f"KPI okuma hatasi: {e}")
            return {}

if __name__ == "__main__":
    print("DWSIM Harness modul test asamasinda...")
    print("Kullanim icin scripts/run_phase5_dwsim.py veya notebook kullanin.")
