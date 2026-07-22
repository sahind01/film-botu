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
    """Extractor link sınıfı - Kotlin'deki ExtractorLink'e karşılık gelir"""
    def __init__(self, source: str, name: str, url: str, link_type: str, 
                 quality: int = 0, referer: str = "", headers: Dict = None):
        self.source = source
        self.name = name
        self.url = url
        self.type = link_type  # M3U8, DASH, VIDEO
        self.quality = quality
        self.referer = referer
        self.headers = headers or {}


class SubtitleFile:
    """Altyazı dosyası sınıfı - Kotlin'deki SubtitleFile'e karşılık gelir"""
    def __init__(self, url: str, lang: str = "tr"):
        self.url = url
        self.lang = lang


class ExtractorAPI:
    """Temel çıkarıcı API sınıfı - Kotlin'deki ExtractorApi'ye karşılık gelir"""
    def __init__(self):
        self.name = ""
        self.main_url = ""
        self.requires_referer = False
    
    def get_url(self, url: str, referer: str = None, 
                subtitle_callback: Callable = None, 
                link_callback: Callable = None):
        raise NotImplementedError


class CDNJWPlayer(ExtractorAPI):
    """CDN JWPlayer çıkarıcı - Kotlin'deki CDNJWPlayer sınıfı"""
    def __init__(self):
        super().__init__()
        self.name = "CDN JWPlayer"
        self.main_url = "https://cdn.jwplayer.com"
        self.requires_referer = False
    
    def get_url(self, url: str, referer: str = None,
                subtitle_callback: Callable = None,
                link_callback: Callable = None):
        logger.debug(f"CDNJWPlayer get_url: {url}")
        if link_callback:
            link_callback(ExtractorLink(
                source=self.name,
                name=self.name,
                url=url,
                link_type="M3U8",
                quality=0
            ))


class DiskYandexComTr(ExtractorAPI):
    """Yandex Disk çıkarıcı - Kotlin'deki DiskYandexComTr sınıfı"""
    def __init__(self):
        super().__init__()
        self.name = "DiskYandexComTr"
        self.main_url = "https://disk.yandex.com.tr"
        self.requires_referer = False
        self.master_playlist_regex = re.compile(r'https?://[^\s"]*?master-playlist\.m3u8')
    
    def get_url(self, url: str, referer: str = None,
                subtitle_callback: Callable = None,
                link_callback: Callable = None):
        logger.debug(f"DiskYandexComTr get_url: {url}")
        
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://disk.yandex.com.tr/"
        }
        
        try:
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
        except Exception as e:
            logger.error(f"DiskYandexComTr hatası: {e}")
            raise


class DzenRu(ExtractorAPI):
    """Dzen.ru çıkarıcı - Kotlin'deki DzenRu sınıfı"""
    def __init__(self):
        super().__init__()
        self.name = "DzenRu"
        self.main_url = "https://dzen.ru/"
        self.requires_referer = False
    
    def get_url(self, url: str, referer: str = None,
                subtitle_callback: Callable = None,
                link_callback: Callable = None):
        logger.debug(f"DzenRu get_url: {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.38 Mobile Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.main_url
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return
            
            # Stream verilerini bul - Kotlin'deki script seçici mantığı
            script_match = re.search(r'"streams":\s*\[(.*?)\]', response.text, re.DOTALL)
            if not script_match:
                return
            
            try:
                streams_data = json.loads(f'[{script_match.group(1)}]')
            except json.JSONDecodeError:
                return
            
            for stream in streams_data:
                stream_type = stream.get("type", "")
                stream_url = stream.get("url", "")
                
                # Kalite belirleme - Kotlin'deki kalite mantığı
                quality_map = {
                    "fullhd": 1080,
                    "high": 720,
                    "medium": 480,
                    "low": 360,
                    "lowest": 240,
                    "tiny": 144
                }
                quality = 0
                for key, value in quality_map.items():
                    if key in stream_type.lower():
                        quality = value
                        break
                
                # Kotlin'deki when mantığı
                if stream_type == "hls":
                    link_type = "M3U8"
                    source_name = f"{self.name} - HLS"
                elif stream_type == "dash":
                    link_type = "DASH"
                    source_name = f"{self.name} - DASH"
                else:
                    link_type = "VIDEO"
                    quality_name = self._get_quality_name(quality)
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
        except Exception as e:
            logger.error(f"DzenRu hatası: {e}")
    
    def _get_quality_name(self, quality: int) -> str:
        """Kalite değerine göre isim döndür - Kotlin'deki getStringByInt'e karşılık"""
        quality_map = {
            1080: "1080p",
            720: "720p",
            480: "480p",
            360: "360p",
            240: "240p",
            144: "144p"
        }
        return quality_map.get(quality, "Unknown")


class FilmizleeeeeExtractor(ExtractorAPI):
    """Filmizleeeee çıkarıcı - Kotlin'deki FilmizleeeeeExtractor sınıfı"""
    def __init__(self):
        super().__init__()
        self.name = "Filmizleeeee"
        self.main_url = "https://embed.filmizleeeee.cfd"
        self.requires_referer = True
    
    def get_url(self, url: str, referer: str = None,
                subtitle_callback: Callable = None,
                link_callback: Callable = None):
        logger.debug(f"FilmizleeeeeExtractor get_url: {url}")
        
        try:
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
        except Exception as e:
            logger.error(f"FilmizleeeeeExtractor hatası: {e}")


class ChContent:
    """İçerik sınıfı - Kotlin'deki ChContent data class'ı"""
    def __init__(self, ch_name: str, ch_url: str, ch_img: str, 
                 ch_headers: str, ch_reg: str, ch_type: str):
        self.ch_name = ch_name
        self.ch_url = ch_url
        self.ch_img = ch_img
        self.ch_headers = ch_headers
        self.ch_reg = ch_reg
        self.ch_type = ch_type


class InatBox:
    """İnatBox ana sınıfı - Kotlin'deki InatBox sınıfı"""
    
    DEFAULT_CONTENT_URL = "https://static.staticsave.com/fast/ct.js"
    DOMAIN_SOURCE_URL = "https://raw.githubusercontent.com/mtlshash/cert/main/hash"
    MASTER_AES_KEY = "ywevqtjrurkwtqgz"
    
    def __init__(self):
        self.name = "Brosvod • InatBox"
        self.lang = "tr"
        self.has_main_page = True
        self.has_quick_search = True
        self.supported_types = ["Movie", "TvSeries", "Live"]
        self.get_main_page_timeout_ms = 25000
        self.sequential_main_page = False
        
        self.aes_key = self.MASTER_AES_KEY
        self.content_url = self._resolve_content_url()
        self.url_to_search_response = {}
        
        logger.info(f"İnatBox başlatıldı, content_url: {self.content_url}")
    
    def _resolve_content_url(self) -> str:
        """Dinamik içerik URL'sini çöz - Kotlin'deki resolveContentUrl fonksiyonu"""
        try:
            response = requests.get(self.DOMAIN_SOURCE_URL)
            if response.status_code != 200:
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
        """AES CBC şifre çözme - Kotlin'deki decryptAes fonksiyonu"""
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
        """Şifreli yanıttan JSON çıkar - Kotlin'deki getJsonFromEncryptedInatResponse"""
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
        """İnatBox API isteği yap - Kotlin'deki makeInatRequest"""
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
                "User-Agent": "speedrestapi"
            }
            
            key_str = key or self.aes_key
            body = f"1={key_str}&0={key_str}"
            
            response = requests.post(url, headers=headers, data=body)
            if response.status_code != 200:
                logger.error(f"İstek başarısız: {response.status_code}")
                return None
            
            return self._get_json_from_encrypted_response(response.text, key_str)
        except Exception as e:
            logger.error(f"İstek hatası: {e}")
            return None
    
    def _make_inat_request_with_key(self, url: str, request_key: str) -> Optional[Dict]:
        """Belirli anahtarla istek yap - Kotlin'deki makeInatRequestWithKey"""
        return self._make_inat_request(url, request_key)
    
    def _parse_to_ch_content(self, item: Dict) -> ChContent:
        """JSON'dan ChContent oluştur - Kotlin'deki parseToChContent"""
        return ChContent(
            ch_name=item.get("chName", ""),
            ch_url=self._vk_source_fix(item.get("chUrl", "")),
            ch_img=item.get("chImg", ""),
            ch_headers=item.get("chHeaders", "null"),
            ch_reg=item.get("chReg", "null"),
            ch_type=item.get("chType", "")
        )
    
    def _vk_source_fix(self, url: str) -> str:
        """VK kaynak düzeltmesi - Kotlin'deki vkSourceFix"""
        if url.startswith("act"):
            return f"https://vk.com/al_video.php?{url}"
        return url
    
    def _playback_headers(self, ch_content: ChContent) -> Dict[str, str]:
        """Oynatma başlıklarını oluştur - Kotlin'deki playbackHeaders"""
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
    
    def _is_direct_stream(self, url: str) -> bool:
        """Doğrudan stream mi kontrol et - Kotlin'deki isDirectStream"""
        return any(x in url.lower() for x in [".m3u8", ".mpd", ".mp4", ".mkv", ".webm"])
    
    def _inat_content_allowed(self, item: Dict) -> bool:
        """İçerik izinli mi kontrol et - Kotlin'deki inatContentAllowed"""
        type_val = item.get("diziType") or item.get("chType", "")
        return type_val.lower() not in ["link", "web"]
    
    def fetch_main_page(self) -> List[Dict]:
        """Ana sayfayı getir - Kotlin'deki getMainPage'e karşılık"""
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
        except Exception as e:
            logger.error(f"Ana sayfa hatası: {e}")
            return []
    
    def get_search_response_list(self, json_response: str) -> List[Dict]:
        """Arama sonuçlarını parse et - Kotlin'deki getSearchResponseList"""
        results = []
        
        try:
            items = json.loads(json_response)
            if not isinstance(items, list):
                items = [items]
            
            for item in items:
                if not self._inat_content_allowed(item):
                    continue
                
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
    
    def search(self, query: str) -> List[Dict]:
        """Arama yap - Kotlin'deki search"""
        try:
            # Ana sayfayı fetch et
            categories = self.fetch_main_page()
            for category in categories:
                category_url = category.get("catUrl")
                if category_url:
                    data = self._make_inat_request(category_url)
                    if data:
                        results = self.get_search_response_list(json.dumps(data))
                        for result in results:
                            self.url_to_search_response[result["url"]] = result
            
            # Arama yap
            results = []
            for item in self.url_to_search_response.values():
                if query.lower() in item["name"].lower():
                    results.append(item)
            
            return results
        except Exception as e:
            logger.error(f"Arama hatası: {e}")
            return []
    
    def load(self, url: str) -> Optional[Dict]:
        """İçerik yükle - Kotlin'deki load"""
        try:
            item = json.loads(url)
            
            if not self._inat_content_allowed(item):
                return None
            
            if "diziType" in item:
                return self._parse_tv_series_response(item)
            elif all(k in item for k in ["chName", "chUrl", "chImg"]):
                return self._parse_live_stream_response(item)
            else:
                return None
        except Exception as e:
            logger.error(f"Load hatası: {e}")
            return None
    
    def _parse_tv_series_response(self, item: Dict) -> Optional[Dict]:
        """TV dizisi yanıtını parse et - Kotlin'deki parseTvSeriesResponse"""
        try:
            name = item.get("diziName", "")
            url = item.get("diziUrl", "")
            plot = item.get("diziDetay", "")
            
            json_response = self._make_inat_request(url)
            if not json_response:
                return None
            
            episodes = []
            season_data = []
            
            for i, season_item in enumerate(json_response):
                season_name = season_item.get("diziName", "")
                season_data.append({"season": i + 1, "name": season_name})
                
                season_url = season_item.get("diziUrl")
                if season_url:
                    episode_response = self._make_inat_request(season_url)
                    if episode_response:
                        for j, episode_item in enumerate(episode_response):
                            episode_name = episode_item.get("chName", "")
                            episode_poster = episode_item.get("chImg", "")
                            episodes.append({
                                "name": episode_name,
                                "poster_url": episode_poster,
                                "season": i + 1,
                                "episode": j + 1,
                                "data": json.dumps(episode_item)
                            })
            
            poster_url = json_response[0].get("diziImg", "") if json_response else ""
            
            return {
                "name": name,
                "url": json.dumps(item),
                "type": "TvSeries",
                "poster_url": poster_url,
                "plot": plot,
                "episodes": episodes,
                "season_data": season_data
            }
        except Exception as e:
            logger.error(f"TV dizisi parse hatası: {e}")
            return None
    
    def _parse_live_stream_response(self, item: Dict) -> Optional[Dict]:
        """Canlı yayın yanıtını parse et - Kotlin'deki parseLiveStreamLoadResponse"""
        try:
            ch_content = self._parse_to_ch_content(item)
            return {
                "name": ch_content.ch_name,
                "url": json.dumps(item),
                "type": "Live",
                "poster_url": ch_content.ch_img,
                "ch_content": ch_content
            }
        except Exception as e:
            logger.error(f"Canlı yayın parse hatası: {e}")
            return None
    
    def load_links(self, data: str, subtitle_callback: Callable = None, 
                   link_callback: Callable = None) -> bool:
        """Linkleri yükle - Kotlin'deki loadLinks"""
        logger.debug(f"load_links data: {data}")
        
        try:
            # Tekli içerik kontrolü
            single = json.loads(data)
            if isinstance(single, dict):
                ch_type = single.get("chType", "")
                if "SsprDrm" in ch_type:
                    raw = single.get("chUrl", "")
                    stream_id = raw.split('/')[-1].split('?')[0].split('.')[0]
                    if stream_id:
                        if link_callback:
                            link_callback(ExtractorLink(
                                source="Ssport",
                                name=single.get("chName", "Ssport"),
                                url=f"https://sspplus.redzones.icu/CDN/SSP/txt/{stream_id}.m3u8",
                                link_type="M3U8",
                                quality=0,
                                referer="https://google.com/"
                            ))
                        return True
            
            # JSON Array kontrolü
            items = json.loads(data) if isinstance(data, str) else data
            if not isinstance(items, list):
                items = [items]
            
            for item in items:
                ch_content = self._parse_to_ch_content(item)
                self._load_ch_content_links(ch_content, subtitle_callback, link_callback)
            
            return True
        except Exception as e:
            logger.error(f"load_links hatası: {e}")
            return False
    
    def _load_ch_content_links(self, ch_content: ChContent, 
                               subtitle_callback: Callable = None,
                               link_callback: Callable = None):
        """İçerik linklerini yükle - Kotlin'deki loadChContentLinks"""
        try:
            content_to_process = ch_content
            
            # Özel tip kontrolü
            if "tekli_regex_lb_sh_3" in ch_content.ch_type.lower():
                regex_key = self.aes_key
                try:
                    if ch_content.ch_reg != "null":
                        reg_data = json.loads(ch_content.ch_reg)
                        if reg_data and len(reg_data) > 0:
                            regex_key = reg_data[0].get("Regex1", self.aes_key)
                except:
                    pass
                
                json_response = self._make_inat_request_with_key(ch_content.ch_url, regex_key)
                if not json_response:
                    try:
                        encrypted_response = requests.get(ch_content.ch_url).text
                        json_response = self._get_json_from_encrypted_response(encrypted_response, regex_key)
                    except:
                        pass
                
                if json_response:
                    item = json_response if isinstance(json_response, dict) else {}
                    item["chHeaders"] = ch_content.ch_headers
                    item["chReg"] = ch_content.ch_reg
                    item["chName"] = ch_content.ch_name
                    item["chImg"] = ch_content.ch_img
                    item["chType"] = ch_content.ch_type
                    content_to_process = self._parse_to_ch_content(item)
            
            source_url = content_to_process.ch_url
            headers = self._playback_headers(content_to_process)
            
            # Doğrudan stream mi?
            if self._is_direct_stream(source_url):
                link_type = "M3U8" if ".m3u8" in source_url.lower() else \
                           "DASH" if ".mpd" in source_url.lower() else "VIDEO"
                
                if link_callback:
                    link_callback(ExtractorLink(
                        source=self.name,
                        name=content_to_process.ch_name,
                        url=source_url,
                        link_type=link_type,
                        quality=0,
                        referer=headers.get("Referer", ""),
                        headers=headers
                    ))
                return
            
            # Extractor'ları dene
            extractors = [CDNJWPlayer(), DiskYandexComTr(), DzenRu(), FilmizleeeeeExtractor()]
            extractor_found = False
            
            for extractor in extractors:
                try:
                    extractor.get_url(source_url, link_callback=link_callback)
                    extractor_found = True
                    break
                except:
                    continue
            
            # Hiçbir extractor bulamadıysa direkt link olarak ekle
            if not extractor_found and link_callback:
                link_callback(ExtractorLink(
                    source=self.name,
                    name=content_to_process.ch_name,
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
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write(f"# Playlist oluşturulma: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
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
    
    for category in categories[:5]:
        print(f"- {category.get('catName', 'Unknown')}")
    
    if categories:
        # İlk kategoriden içerik al
        first_category = categories[0]
        category_url = first_category.get("catUrl")
        category_name = first_category.get("catName", "Kategori")
        
        if category_url:
            print(f"\n=== {category_name} Kategorisi Detayları ===")
            data = inat._make_inat_request(category_url)
            
            if data:
                results = inat.get_search_response_list(json.dumps(data))
                print(f"Bulunan içerik: {len(results)}")
                
                all_links = []
                
                # İlk 5 içeriği işle
                for idx, result in enumerate(results[:5]):
                    print(f"\n--- {idx+1}. İçerik: {result['name']} ---")
                    
                    # İçeriği yükle
                    content = inat.load(result["url"])
                    if content:
                        print(f"İçerik türü: {content.get('type')}")
                        
                        # Linkleri al
                        if content.get('type') == 'Live':
                            ch_content = content.get('ch_content')
                            if ch_content:
                                def collect_link(link: ExtractorLink):
                                    all_links.append(link)
                                    print(f"  Link bulundu: {link.name} - {link.url[:50]}...")
                                
                                inat._load_ch_content_links(ch_content, link_callback=collect_link)
                        
                        elif content.get('type') == 'TvSeries':
                            episodes = content.get('episodes', [])
                            if episodes:
                                # İlk bölümü al
                                first_episode = episodes[0]
                                print(f"  İlk bölüm: {first_episode['name']}")
                                
                                def collect_link(link: ExtractorLink):
                                    all_links.append(link)
                                    print(f"  Link bulundu: {link.name} - {link.url[:50]}...")
                                
                                episode_item = json.loads(first_episode['data'])
                                ch_content = inat._parse_to_ch_content(episode_item)
                                inat._load_ch_content_links(ch_content, link_callback=collect_link)
                
                # M3U oluştur
                if all_links:
                    print(f"\n=== Toplam {len(all_links)} link bulundu ===")
                    create_m3u(all_links, "inatbox_playlist.m3u")
                    print("✅ M3U dosyası oluşturuldu: inatbox_playlist.m3u")
                    
                    # Dosya boyutunu göster
                    import os
                    if os.path.exists("inatbox_playlist.m3u"):
                        size = os.path.getsize("inatbox_playlist.m3u")
                        print(f"📁 Dosya boyutu: {size} bytes")
                else:
                    print("❌ Hiç link bulunamadı!")
            else:
                print("❌ Kategori verisi alınamadı!")


if __name__ == "__main__":
    main()
