#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.
Kotlin'den Python'a çevrilmiş M3U link çıkarıcı
"""

import re
import json
import base64
import requests
from typing import List, Dict, Optional, Callable
from urllib.parse import urlparse
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class ExtractorLink:
    def __init__(self, source: str, name: str, url: str, link_type: str, 
                 quality: int = 0, referer: str = "", headers: Dict = None):
        self.source = source
        self.name = name
        self.url = url
        self.type = link_type
        self.quality = quality
        self.referer = referer
        self.headers = headers or {}


class ExtractorApi:
    def __init__(self):
        self.name = ""
        self.main_url = ""
        self.requires_referer = False
    
    def get_url(self, url: str, referer: str = None, link_callback: Callable = None):
        raise NotImplementedError


class CDNJWPlayer(ExtractorApi):
    def __init__(self):
        super().__init__()
        self.name = "CDN JWPlayer"
        self.main_url = "https://cdn.jwplayer.com"
        self.requires_referer = False
    
    def get_url(self, url: str, referer: str = None, link_callback: Callable = None):
        if link_callback:
            link_callback(ExtractorLink(
                source=self.name,
                name=self.name,
                url=url,
                link_type="M3U8",
                quality=0
            ))


class DiskYandexComTr(ExtractorApi):
    def __init__(self):
        super().__init__()
        self.name = "DiskYandexComTr"
        self.main_url = "https://disk.yandex.com.tr"
        self.requires_referer = False
        self.master_playlist_regex = re.compile(r'https?://[^\s"]*?master-playlist\.m3u8')
    
    def get_url(self, url: str, referer: str = None, link_callback: Callable = None):
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://disk.yandex.com.tr/"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch URL: {response.status_code}")
        
        match = self.master_playlist_regex.search(response.text)
        if match:
            master_playlist_url = match.group()
            if link_callback:
                link_callback(ExtractorLink(
                    source="Yandex Disk",
                    name="Yandex Disk",
                    url=master_playlist_url,
                    link_type="M3U8",
                    quality=0
                ))
        else:
            raise Exception("No master-playlist.m3u8 URL found in the response")


class DzenRu(ExtractorApi):
    def __init__(self):
        super().__init__()
        self.name = "DzenRu"
        self.main_url = "https://dzen.ru/"
        self.requires_referer = False
    
    def get_url(self, url: str, referer: str = None, link_callback: Callable = None):
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.38 Mobile Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.main_url
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return
        
        script_match = re.search(r'"streams":\s*\[(.*?)\]', response.text, re.DOTALL)
        if not script_match:
            return
        
        try:
            streams_data = json.loads(f'[{script_match.group(1)}]')
        except:
            return
        
        for stream in streams_data:
            stream_type = stream.get("type", "")
            stream_url = stream.get("url", "")
            
            # Kalite belirleme
            if "fullhd" in stream_type:
                quality = 1080
            elif "high" in stream_type:
                quality = 720
            elif "medium" in stream_type:
                quality = 480
            elif "low" in stream_type:
                quality = 360
            elif "lowest" in stream_type:
                quality = 240
            elif "tiny" in stream_type:
                quality = 144
            else:
                quality = 0
            
            # Kalite ismi
            quality_names = {1080: "1080p", 720: "720p", 480: "480p", 360: "360p", 240: "240p", 144: "144p"}
            quality_name = quality_names.get(quality, "Unknown")
            
            if stream_type == "hls":
                link_type = "M3U8"
                source_name = f"{self.name} - HLS"
            elif stream_type == "dash":
                link_type = "DASH"
                source_name = f"{self.name} - DASH"
            else:
                link_type = "VIDEO"
                source_name = f"{self.name} - {quality_name}"
            
            if link_callback and stream_url:
                link_callback(ExtractorLink(
                    source=source_name,
                    name=source_name,
                    url=stream_url,
                    link_type=link_type,
                    quality=quality,
                    referer=""
                ))


class FilmizleeeeeExtractor(ExtractorApi):
    def __init__(self):
        super().__init__()
        self.name = "Filmizleeeee"
        self.main_url = "https://embed.filmizleeeee.cfd"
        self.requires_referer = True
    
    def get_url(self, url: str, referer: str = None, link_callback: Callable = None):
        headers = {"Referer": referer or self.main_url}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200 or not response.text.strip():
            return
        
        if link_callback:
            link_callback(ExtractorLink(
                source=self.name,
                name=self.name,
                url=response.text.strip(),
                link_type="VIDEO",
                quality=0,
                referer=referer or self.main_url
            ))


class ChContent:
    def __init__(self, ch_name: str, ch_url: str, ch_img: str, 
                 ch_headers: str, ch_reg: str, ch_type: str):
        self.ch_name = ch_name
        self.ch_url = ch_url
        self.ch_img = ch_img
        self.ch_headers = ch_headers
        self.ch_reg = ch_reg
        self.ch_type = ch_type


class InatBox:
    DEFAULT_CONTENT_URL = "https://static.staticsave.com/fast/ct.js"
    DOMAIN_SOURCE_URL = "https://raw.githubusercontent.com/mtlshash/cert/main/hash"
    MASTER_AES_KEY = "ywevqtjrurkwtqgz"
    
    def __init__(self):
        self.name = "Brosvod • InatBox"
        self.aes_key = self.MASTER_AES_KEY
        self.content_url = self._resolve_content_url()
        self.url_to_search_response = {}
    
    def _resolve_content_url(self) -> str:
        try:
            response = requests.get(self.DOMAIN_SOURCE_URL)
            if response.status_code != 200:
                return self.DEFAULT_CONTENT_URL
            
            encrypted = response.text.replace("-----BEGIN CERTIFICATE-----", "").replace("-----END CERTIFICATE-----", "").strip()
            
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
        except:
            return self.DEFAULT_CONTENT_URL
    
    def _decrypt_aes(self, cipher_text: str, key: str) -> str:
        try:
            try:
                key_bytes = base64.b64decode(key)
                if len(key_bytes) not in [16, 24, 32]:
                    key_bytes = key.encode('utf-8')
            except:
                key_bytes = key.encode('utf-8')
            
            cipher = AES.new(key_bytes, AES.MODE_CBC, key_bytes[:16])
            decrypted = unpad(cipher.decrypt(base64.b64decode(cipher_text)), AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise Exception(f"AES decrypt failed: {e}")
    
    def _get_json_from_encrypted_response(self, response_text: str, key: str = None) -> Optional[Dict]:
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
        except:
            return None
    
    def _make_inat_request(self, url: str, key: str = None) -> Optional[Dict]:
        try:
            hostname = urlparse(url).hostname
            if not hostname:
                return None
            
            headers = {
                "Cache-Control": "no-cache",
                "Content-Length": "37",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Host": hostname,
                "Referer": "https://speedrestapi.com/",
                "X-Requested-With": "com.bp.box",
                "User-Agent": "speedrestapi"
            }
            
            key_str = key or self.aes_key
            body = f"1={key_str}&0={key_str}"
            
            response = requests.post(url, headers=headers, data=body)
            if response.status_code != 200:
                return None
            
            return self._get_json_from_encrypted_response(response.text, key_str)
        except:
            return None
    
    def _parse_to_ch_content(self, item: Dict) -> ChContent:
        url = item.get("chUrl", "")
        if url.startswith("act"):
            url = f"https://vk.com/al_video.php?{url}"
        
        return ChContent(
            ch_name=item.get("chName", ""),
            ch_url=url,
            ch_img=item.get("chImg", ""),
            ch_headers=item.get("chHeaders", "null"),
            ch_reg=item.get("chReg", "null"),
            ch_type=item.get("chType", "")
        )
    
    def _playback_headers(self, ch_content: ChContent) -> Dict[str, str]:
        headers = {}
        
        try:
            if ch_content.ch_headers != "null":
                json_headers = json.loads(ch_content.ch_headers)
                if json_headers and len(json_headers) > 0:
                    for key, value in json_headers[0].items():
                        header_name = "User-Agent" if key == "UserAgent" else "X-Requested-With" if key == "XRequestedWith" else key
                        headers[header_name] = value
            
            if ch_content.ch_reg != "null":
                json_reg = json.loads(ch_content.ch_reg)
                if json_reg and len(json_reg) > 0:
                    play_sh2 = json_reg[0].get("playSH2", "")
                    if play_sh2:
                        headers["Cookie"] = play_sh2
        except:
            pass
        
        return headers
    
    def _is_direct_stream(self, url: str) -> bool:
        return any(x in url.lower() for x in [".m3u8", ".mpd", ".mp4", ".mkv", ".webm"])
    
    def fetch_main_page(self) -> List[Dict]:
        try:
            response = requests.get(self.content_url)
            if response.status_code != 200:
                return []
            
            categories_json = self._get_json_from_encrypted_response(response.text)
            if not categories_json:
                return []
            
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
        except:
            return []
    
    def get_search_response_list(self, json_response: str) -> List[Dict]:
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
        except:
            pass
        
        return results
    
    def load_links(self, data: str, link_callback: Callable = None) -> bool:
        try:
            items = json.loads(data) if isinstance(data, str) else data
            if not isinstance(items, list):
                items = [items]
            
            for item in items:
                ch_content = self._parse_to_ch_content(item)
                self._load_ch_content_links(ch_content, link_callback)
            
            return True
        except:
            return False
    
    def _load_ch_content_links(self, ch_content: ChContent, link_callback: Callable = None):
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
            
            # Extractors dene
            extractors = [CDNJWPlayer(), DiskYandexComTr(), DzenRu(), FilmizleeeeeExtractor()]
            found = False
            
            for extractor in extractors:
                try:
                    extractor.get_url(source_url, link_callback=link_callback)
                    found = True
                    break
                except:
                    continue
            
            if not found and link_callback:
                link_callback(ExtractorLink(
                    source=self.name,
                    name=ch_content.ch_name,
                    url=source_url,
                    link_type="VIDEO",
                    quality=0,
                    referer=headers.get("Referer", ""),
                    headers=headers
                ))
        except:
            pass


def create_m3u(links: List[ExtractorLink], filename: str = "inatbox_playlist.m3u"):
    from datetime import datetime
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write(f"# Playlist created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("#EXTINF:-1, İnatBox Playlist\n")
        
        for link in links:
            f.write(f"#EXTINF:-1,{link.name}\n")
            f.write(f"{link.url}\n")


def main():
    print("=== İnatBox M3U Extractor ===")
    inat = InatBox()
    
    categories = inat.fetch_main_page()
    print(f"Kategori sayısı: {len(categories)}")
    
    all_links = []
    
    for category in categories[:3]:
        category_url = category.get("catUrl")
        category_name = category.get("catName", "Kategori")
        
        if category_url:
            print(f"\nİşleniyor: {category_name}")
            data = inat._make_inat_request(category_url)
            
            if data:
                results = inat.get_search_response_list(json.dumps(data))
                print(f"  {len(results)} içerik bulundu")
                
                for result in results[:2]:
                    print(f"  - {result['name']}")
                    
                    def collect_link(link: ExtractorLink):
                        all_links.append(link)
                    
                    inat.load_links(result["url"], link_callback=collect_link)
    
    if all_links:
        print(f"\n{len(all_links)} link bulundu")
        create_m3u(all_links)
        print("✅ M3U oluşturuldu: inatbox_playlist.m3u")
    else:
        print("❌ Link bulunamadı")


if __name__ == "__main__":
    main()
