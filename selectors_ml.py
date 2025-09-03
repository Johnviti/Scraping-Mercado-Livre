# selectors_ml.py
import re
from bs4 import BeautifulSoup

def text_or_none(node):
    return node.get_text(" ", strip=True) if node else None

def clean_price(fraction, cents):
    if not fraction and not cents:
        return None
    if not cents or not re.search(r"\d", cents):
        return fraction
    return f"{fraction},{cents}"

def normalize_link(href):
    if not href:
        return None, False
    is_tracking = "click1.mercadolivre.com.br" in href
    return href, is_tracking

def parse_list_items(html):
    soup = BeautifulSoup(html, "lxml")

    items = []
    # layout “novo” com <li>
    for li in soup.select("li.ui-search-layout__item"):
        a_title = li.select_one("h3.poly-component__title-wrapper > a.poly-component__title, a.poly-component__title")
        title = text_or_none(a_title)
        href_raw = a_title["href"] if a_title and a_title.has_attr("href") else None
        link, is_tracking = normalize_link(href_raw)

        brand = text_or_none(li.select_one(".poly-component__brand"))
        seller = text_or_none(li.select_one(".poly-component__seller"))

        rating = text_or_none(li.select_one(".poly-component__reviews .poly-reviews__rating"))
        reviews_total = text_or_none(li.select_one(".poly-component__reviews .poly-reviews__total"))

        frac = li.select_one(".poly-price__current .andes-money-amount__fraction, .andes-money-amount__fraction")
        cents = li.select_one(".poly-price__current .andes-money-amount__cents, .andes-money-amount__cents")
        price = clean_price(frac.get_text(strip=True) if frac else None,
                            cents.get_text(strip=True) if cents else None)

        prev_frac = li.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
        prev_cents = li.select_one(".andes-money-amount--previous .andes-money-amount__cents")
        previous_price = clean_price(prev_frac.get_text(strip=True) if prev_frac else None,
                                     prev_cents.get_text(strip=True) if prev_cents else None)

        discount = text_or_none(li.select_one(".andes-money-amount__discount"))
        shipping = text_or_none(li.select_one(".poly-component__shipping"))
        sponsored = li.select_one(".poly-component__ads-promotions") is not None

        img = None
        img_tag = li.select_one(".poly-card__portada img.poly-component__picture[aria-hidden='true'], .poly-card__portada img.poly-component__picture")
        if not img_tag:
            img_tag = li.select_one(".andes-carousel-snapped__slide img.poly-component__picture")
        
        if img_tag:
            # Tenta buscar URL real da imagem em diferentes atributos
            # Prioriza atributos que geralmente contêm URLs reais
            for attr in ['data-src', 'data-original', 'data-lazy', 'data-zoom', 'src']:
                if img_tag.has_attr(attr):
                    potential_img = img_tag[attr]
                    # Verifica se não é um placeholder base64
                    if potential_img and not potential_img.startswith('data:image/gif;base64,'):
                        img = potential_img
                        break
            
            # Se ainda não encontrou uma imagem válida, usa o src mesmo que seja placeholder
            if not img and img_tag.has_attr("src"):
                img = img_tag["src"]

        if any([title, price, link]):
            items.append({
                "title": title,
                "price": price,
                "previous_price": previous_price,
                "discount": discount,
                "brand": brand,
                "seller": seller,
                "rating": rating,
                "reviews_total": reviews_total,
                "shipping": shipping,
                "sponsored": sponsored,
                "link": link,
                "is_tracking_link": is_tracking,
                "image": img,
            })

    # fallback: cards sem <li>
    if not items:
        for card in soup.select("div.poly-card__content"):
            a_title = card.select_one("a.poly-component__title")
            title = text_or_none(a_title)
            href_raw = a_title["href"] if a_title and a_title.has_attr("href") else None
            link, is_tracking = normalize_link(href_raw)
            frac = card.select_one(".poly-price__current .andes-money-amount__fraction")
            cents = card.select_one(".poly-price__current .andes-money-amount__cents")
            price = clean_price(frac.get_text(strip=True) if frac else None,
                                cents.get_text(strip=True) if cents else None)
            if any([title, price, link]):
                items.append({"title": title, "price": price, "link": link, "is_tracking_link": is_tracking})

    return items
