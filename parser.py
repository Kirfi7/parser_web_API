from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from schemas import ProductBase
import json
import time

def fetch_page(url):
    """
    Функция получения страницы с использованием Selenium
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(1)  # Даем странице время на загрузку контента

    html = driver.page_source
    driver.quit()
    return html


def parse_products_from_cur_page(html):
    """
    Парсим продукты со страницы
    """
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    pydantic_products = []

    # Задаем селектор для карточек товаров
    product_cards = soup.select(".ProductCard_productCard__container__u7Lrh")

    for card in product_cards:
        # Извлекаем название и бренд
        brand = card.select_one(".ProductCard_productCard__brandBlock__kLVj_").get_text(strip=True) if card.select_one(
            ".ProductCard_productCard__brandBlock__kLVj_") else "Бренд не найден"
        title = card.select_one(".ProductCard_productCard__title__cjmjE").get_text(strip=True) if card.select_one(
            ".ProductCard_productCard__title__cjmjE") else "Название не найдено"

        # Извлекаем цену
        price = card.select_one(".ProductCard_productCard__price__R9hLh").get_text(strip=True) if card.select_one(
            ".ProductCard_productCard__price__R9hLh") else "Цена не указана"

        price = int(price.replace('₽', '').replace(' ', '').strip())

        # Добавляем данные в список
        products.append({
            "brand": brand,
            "name": title,
            "price": price
        })

        pydantic_products.append(
            ProductBase(brand=brand, name=title, price=price)
        )


    return products, pydantic_products


def get_all_products():
    """
    Проходимся по всем страницам в новинках
    """
    base_url = "https://bdkids.ru/sale"
    # base_url = "https://bdkids.ru/catalog"
    page_number = 1
    all_products = []
    all_pydantic_products = []

    while True:
        url = f"{base_url}?page={page_number}"
        print(f"Сбор данных со страницы: {url}")

        html = fetch_page(url)
        if html is None:
            break

        products, pydantic_products = parse_products_from_cur_page(html)
        if not products:
            print("Товары не найдены, завершение парсинга.")
            break

        all_products.extend(products)
        all_pydantic_products.extend(pydantic_products)
        page_number += 1

    # Записываем товары в json
    with open('products.json', 'w', encoding='utf-8') as file:
        json.dump(all_products, file, ensure_ascii=False, indent=4)

    return all_products, all_pydantic_products


# Запуск парсера
# products, pydantic_products = get_all_products()

# Вывод собранных данных
# for product in products:
#     print(f"Название: {product['name']}, Бренд: {product['brand']}, Цена: {product['price']}")
#
# print(f"len {len(pydantic_products)}")
#
# for product in pydantic_products:
#     print(product)