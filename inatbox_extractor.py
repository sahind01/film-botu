#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.
Kotlin'den Python'a çevrilmiş M3U link çıkarıcı
"""

import re
import json
import base64
import logging
import requests
from typing import List, Dict, Optional, Callable, Any
from urllib.parse import urlparse
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExtractorLink:
    """Extractor link sınıfı"""
    def __init__(self, source: str, name: str, url: str, link_type: str, 
                 quality: int = 0, referer: str = "", headers: Dict = None):
        self.source = source
        self.name = name
        self.url = url
        self.type = link_type
        self.quality = quality
        self.referer = referer
        self.headers = headers or {}


class ChContent:
    """İçerik sınıfı"""
    def __init__(self, ch_name: str, ch_url: str, ch_img: str, 
                 ch_headers: str, ch_reg: str, ch_type: str):
        self.ch_name = ch_name
        self.ch_url = ch_url
        self.ch_img = ch_img
        self.ch_headers = ch_headers
        self.ch_reg = ch_reg
        self.ch_type = ch_type


class InatBox:
    """İnatBox ana sınıfı"""
    
    DEFAULT_CONTENT_URL = "https://static.staticsave.com/fast/ct.js"
    DOMAIN_SOURCE_URL = "https://raw.githubusercontent.com/mtlshash/cert/main/hash"
    MASTER_AES_KEY = "ywevqtjrurkwtqgz"
    
    def __init__(self):
        self.name = "Brosvod • InatBox"
        self.aes_key = self.MASTER_AES_KEY
        self.content_url = self._resolve_content_url()
        self.url_to_search_response = {}
        
        logger.info(f"İnatBox başlatıldı, content_url: {self.content_url}")
    
    def _resolve_content_url(self) -> str:
        """Dinamik içerik URL'sini çöz"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(self.DOMAIN_SOURCE_URL, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Domain source alınamadı: {response.status_code}")
                return self.DEFAULT_CONTENT_URL
            
            encrypted = response.text.replace("-----BEGIN CERTIFICATE-----", "")\
                                    .replace("-----END CERTIFICATE-----", "").strip()
            
            parts = encrypted.split(":", 1)
            if len(parts) != 2:
                return self.DEFAULT_CONTENT_URL
            
            first_decoded = self._decrypt_aes(parts[0], parts[1])
            parts2 = first_decoded.split(":", 1)
            if len(parts2) != 2:
                return self.DEFAULT_CONTENT_URL
            
            domain_json = self._decrypt_aes(parts2[0], parts2[1])
            data = json.loads(domain_json)
            url = data.get("DC10", self.DEFAULT_CONTENT_URL)
            
            if url.startswith(("http://", "https://")):
                return url
            return self.DEFAULT_CONTENT_URL
        except Exception as e:
            logger.error(f"Content URL çözülemedi: {e}")
            return self.DEFAULT_CONTENT_URL
    
    def _decrypt_aes(self, cipher_text: str, key: str) -> str:
        """AES CBC şifre çözme"""
        try:
            # Base64 çözümleme dene
            try:
                key_bytes = base64.b64decode(key)
                if len(key_bytes) not in [16, 24, 32]:
                    key_bytes = key.encode('utf-8')
            except:
                key_bytes = key.encode('utf-8')
            
            if len(key_bytes) not in [16, 24, 32]:
                raise ValueError(f"Geçersiz AES anahtar uzunluğu: {len(key_bytes)}")
            
            cipher = AES.new(key_bytes, AES.MODE_CBC, key_bytes[:16])
            decrypted = unpad(cipher.decrypt(base64.b64decode(cipher_text)), AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"AES şifre çözme hatası: {e}")
            raise
    
    def _get_json_from_encrypted_response(self, response_text: str, key: str = None) -> Optional[Dict]:
        """Şifreli yanıttan JSON çıkar"""
        try:
            parts = response_text.strip().split(":", 1)
            if len(parts) != 2:
                return None
            
            encrypted_data = parts[0].strip()
            outer_key = parts[1].strip() if parts[1].strip() else (key or self.aes_key)
            
            first_decoded = self._decrypt_aes(encrypted_data, outer_key)
            if not first_decoded:
                return None
            
            inner_parts = first_decoded.split(":", 1)
            if len(inner_parts) == 2:
                final = self._decrypt_aes(inner_parts[0].strip(), inner_parts[1].strip())
                return json.loads(final)
            else:
                return json.loads(first_decoded)
        except Exception as e:
            logger.error(f"JSON çıkarma hatası: {e}")
            return None
    
    def _make_inat_request(self, url: str, key: str = None) -> Optional[Dict]:
        """İnatBox API isteği yap"""
        try:
            hostname = urlparse(url).hostname
            if not hostname:
                logger.error(f"Geçersiz URL: {url}")
                return None
            
            headers = {
                "Cache-Control": "no-cache",
                "Content-Length": "37",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Host": hostname,
                "Referer": "https://speedrestapi.com/",
                "X-Requested-With": "com.bp.box",
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; com.bp.box)"
            }
            
            key_str = key or self.aes_key
            body = f"1={key_str}&0={key_str}"
            
            response = requests.post(url, headers=headers, data=body, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"İstek başarısız: {response.status_code} - {url}")
                return None
            
            return self._get_json_from_encrypted_response(response.text, key_str)
        except Exception as e:
            logger.error(f"İstek hatası: {e}")
            return None
    
    def _parse_to_ch_content(self, item: Dict) -> ChContent:
        """JSON'dan ChContent oluştur"""
        return ChContent(
            ch_name=item.get("chName", ""),
            ch_url=self._vk_source_fix(item.get("chUrl", "")),
            ch_img=item.get("chImg", ""),
            ch_headers=item.get("chHeaders", "null"),
            ch_reg=item.get("chReg", "null"),
            ch_type=item.get("chType", "")
        )
    
    def _vk_source_fix(self, url: str) -> str:
        """VK kaynak düzeltmesi"""
        if url.startswith("act"):
            return f"https://vk.com/al_video.php?{url}"
        return url
    
    def fetch_main_page(self) -> List[Dict]:
        """Ana sayfayı getir"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(self.content_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Ana sayfa alınamadı: {response.status_code}")
                return []
            
            categories_json = self._get_json_from_encrypted_response(response.text)
            if not categories_json:
                # Doğrudan JSON dene
                try:
                    categories_json = json.loads(response.text)
                except:
                    pass
            
            categories = categories_json if isinstance(categories_json, list) else []
            
            if not categories:
                # Alternatif URL dene
                alt_url = "https://diziboxen.help/CDN/001/002/dizibox/ex/index.php"
                response = requests.get(alt_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    categories_json = self._get_json_from_encrypted_response(response.text)
                    categories = categories_json if isinstance(categories_json, list) else []
            
            filtered = []
            for category in categories:
                category_name = category.get("catName", "")
                category_type = category.get("catType", "")
                category_url = category.get("catUrl", "")
                
                if not category_url:
                    continue
                if category_type.lower() in ["link", "destek"]:
                    continue
                if category_name.lower() in ["hata bildir", "derbiler"]:
                    continue
                if "4k-film-exo.php" in category_url or "destek_mode" in category_url:
                    continue
                if "inattv" in category_url or "x.com/" in category_url:
                    continue
                
                filtered.append(category)
            
            return filtered
        except Exception as e:
            logger.error(f"Ana sayfa hatası: {e}")
            return []
    
    def get_search_response_list(self, json_response: str) -> List[Dict]:
        """Arama sonuçlarını parse et"""
        results = []
        
        try:
            items = json.loads(json_response)
            if not isinstance(items, list):
                items = [items]
            
            for item in items:
                if "diziType" in item:
                    name = item.get("diziName", "")
                    type_val = item.get("diziType", "")
                    poster_url = item.get("diziImg", "")
                    
                    search_type = "TvSeries" if type_val.lower() in ["dizi", "dizi_mode"] else "Movie"
                    results.append({
                        "name": name,
                        "url": json.dumps(item),
                        "poster_url": poster_url,
                        "type": search_type
                    })
                elif all(k in item for k in ["chName", "chUrl", "chImg"]):
                    name = item.get("chName", "")
                    poster_url = item.get("chImg", "")
                    ch_type = item.get("chType", "")
                    
                    search_type = "Live" if ch_type.lower() in ["live_url", "tekli_regex_lb_sh_3"] else "Movie"
                    results.append({
                        "name": name,
                        "url": json.dumps(item),
                        "poster_url": poster_url,
                        "type": search_type
                    })
        except Exception as e:
            logger.error(f"Arama sonuçları parse hatası: {e}")
        
        return results
    
    def _is_direct_stream(self, url: str) -> bool:
        """Doğrudan stream mi kontrol et"""
        return any(x in url.lower() for x in [".m3u8", ".mpd", ".mp4", ".mkv", ".webm"])
    
    def _playback_headers(self, ch_content: ChContent) -> Dict[str, str]:
        """Oynatma başlıklarını oluştur"""
        headers = {}
        
        try:
            if ch_content.ch_headers != "null":
                json_headers = json.loads(ch_content.ch_headers)
                if json_headers and len(json_headers) > 0:
                    for key, value in json_headers[0].items():
                        header_name = "User-Agent" if key == "UserAgent" else \
                                     "X-Requested-With" if key == "XRequestedWith" else key
                        headers[header_name] = value
            
            if ch_content.ch_reg != "null":
                json_reg = json.loads(ch_content.ch_reg)
                if json_reg and len(json_reg) > 0:
                    play_sh2 = json_reg[0].get("playSH2", "")
                    if play_sh2:
                        headers["Cookie"] = play_sh2
        except Exception as e:
            logger.warning(f"Oynatma başlıkları okunamadı: {e}")
        
        return headers
    
    def load_links(self, data: str, link_callback: Callable = None) -> bool:
        """Linkleri yükle"""
        logger.debug(f"load_links data: {data[:200]}...")
        
        try:
            items = json.loads(data) if isinstance(data, str) else data
            if not isinstance(items, list):
                items = [items]
            
            for item in items:
                ch_content = self._parse_to_ch_content(item)
                self._load_ch_content_links(ch_content, link_callback)
            
            return True
        except Exception as e:
            logger.error(f"load_links hatası: {e}")
            return False
    
    def _load_ch_content_links(self, ch_content: ChContent, link_callback: Callable = None):
        """İçerik linklerini yükle"""
        try:
            source_url = ch_content.ch_url
            headers = self._playback_headers(ch_content)
            
            if self._is_direct_stream(source_url):
                if link_callback:
                    link_callback(ExtractorLink(
                        source=self.name,
                        name=ch_content.ch_name,
                        url=source_url,
                        link_type="M3U8" if ".m3u8" in source_url.lower() else "VIDEO",
                        quality=0,
                        referer=headers.get("Referer", ""),
                        headers=headers
                    ))
                return
            
            # Doğrudan link olarak ekle
            if link_callback:
                link_callback(ExtractorLink(
                    source=self.name,
                    name=ch_content.ch_name,
                    url=source_url,
                    link_type="VIDEO",
                    quality=0,
                    referer=headers.get("Referer", ""),
                    headers=headers
                ))
        except Exception as e:
            logger.error(f"load_ch_content_links hatası: {e}")


# M3U dosyası oluşturma fonksiyonu
def create_m3u(links: List[ExtractorLink], filename: str = "playlist.m3u"):
    """ExtractorLink listesinden M3U dosyası oluştur"""
    from datetime import datetime
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write(f"# Playlist oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        for link in links:
            f.write(f"#EXTINF:-1,{link.name}\n")
            f.write(f"{link.url}\n")


# Ana çalıştırma
def main():
    print("=== İnatBox M3U Extractor Başlatılıyor ===")
    inat = InatBox()
    
    print("\n=== Ana Sayfa Kategorileri ===")
    categories = inat.fetch_main_page()
    print(f"Toplam kategori: {len(categories)}")
    
    for category in categories[:10]:
        print(f"- {category.get('catName', 'Unknown')}")
    
    if categories:
        # Tüm kategorilerden içerik topla
        all_links = []
        
        for idx, category in enumerate(categories[:5]):  # İlk 5 kategori
            category_url = category.get("catUrl")
            category_name = category.get("catName", "Kategori")
            
            if category_url:
                print(f"\n=== {category_name} Kategorisi işleniyor... ===")
                data = inat._make_inat_request(category_url)
                
                if data:
                    results = inat.get_search_response_list(json.dumps(data))
                    print(f"  Bulunan içerik: {len(results)}")
                    
                    # İlk 3 içeriği işle
                    for result in results[:3]:
                        print(f"  - {result['name']}")
                        
                        # Linkleri al
                        def collect_link(link: ExtractorLink):
                            all_links.append(link)
                            print(f"    Link bulundu: {link.name}")
                        
                        inat.load_links(result["url"], link_callback=collect_link)
        
        # M3U oluştur
        if all_links:
            print(f"\n=== Toplam {len(all_links)} link bulundu ===")
            create_m3u(all_links, "inatbox_playlist.m3u")
            print("✅ M3U dosyası oluşturuldu: inatbox_playlist.m3u")
            
            import os
            if os.path.exists("inatbox_playlist.m3u"):
                size = os.path.getsize("inatbox_playlist.m3u")
                print(f"📁 Dosya boyutu: {size} bytes")
                
                # İlk 5 linki göster
                print("\n=== İlk 5 Link ===")
                for link in all_links[:5]:
                    print(f"- {link.name}: {link.url[:80]}...")
        else:
            print("❌ Hiç link bulunamadı!")
    else:
        print("❌ Kategori bulunamadı!")


if __name__ == "__main__":
    main()
