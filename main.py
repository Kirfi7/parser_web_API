from fastapi import FastAPI, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from parser import get_all_products
from database import SessionLocal, Product, create_product, get_product_by_id, update_product, delete_product
from websocket_custom import ConnectionManager

app = FastAPI()

# Экземпляр менеджера соединений
manager = ConnectionManager()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Фоновая задача для парсинга и сохранения продуктов в базе данных
async def background_parse(db: Session):
    products, _ = get_all_products()
    try:
        for product in products:
            create_product(db, brand=product["brand"], name=product["name"], price=product["price"])
            # Отправка уведомления через WebSocket
            await manager.send_message(f"Создан новый продукт: {product['name']} - {product['price']}₽")
        print("Записали товары в базу")
    except Exception as e:
        print(f"Возникла ошибка при записи товаров в базу: {e}")

@app.get("/parse", tags=["Парсер"])
async def parse_products(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(background_parse, db)
    await manager.send_message("Парсинг запущен в фоновом режиме.")
    return {"status": "Парсинг запущен в фоновом режиме"}

@app.get("/parse-products", tags=["Парсер"])
async def parse_products_route():
    # Получаем HTML-страницу
    await manager.send_message(f"Запущен парсинг продуктов")
    products = get_all_products()

    return products

@app.get("/get-product", tags=["Действия с базой"])
async def read_product(product_id: int, db: Session = Depends(get_db)):
    product = get_product_by_id(db, product_id)
    if product:
        await manager.send_message(f"Продукт найден: {product.name}")
        return product
    await manager.send_message(f"Продукт с ID {product_id} не найден.")
    raise HTTPException(status_code=404, detail="Продукт не найден")

@app.post("/products", tags=["Действия с базой"])
async def create_product_route(brand: str, name: str, price: int, db: Session = Depends(get_db)):
    """
    Создает продукт, если он еще не существует в базе данных.
    """
    product = create_product(db, brand=brand, name=name, price=price)
    if product:
        # Отправка уведомления через WebSocket
        # print("Попытка отправить сообщение через WebSocket...")
        await manager.send_message(f"Создан новый продукт: {product.name} - {product.price}₽")
        return product
    raise HTTPException(status_code=400, detail="Ошибка при создании продукта.")

@app.put("/products/{product_id}", tags=["Действия с базой"])
async def edit_product(product_id: int, name: str, price: int, brand: str = None, db: Session = Depends(get_db)):
    product = update_product(db, product_id, name=name, price=price, brand=brand)
    if product:
        # Отправляем уведомление
        await manager.send_message(f"Продукт обновлен: {product.name} - {product.price}₽")
        return product
    await manager.send_message(f"Не удалось обновить продукт с ID {product_id}.")
    raise HTTPException(status_code=404, detail="Продукт не найден")

@app.delete("/products/{product_id}", tags=["Действия с базой"])
async def remove_product(product_id: int, db: Session = Depends(get_db)):
    result = delete_product(db, product_id)
    if result:
        await manager.send_message(f"Продукт id: {product_id} удален")
        return {"status": "Продукт удален"}
    await manager.send_message(f"Продукт с ID {product_id} не найден.")
    raise HTTPException(status_code=404, detail="Продукт не найден")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket для уведомлений
    """
    await manager.connect(websocket)
    try:
        while True:
            # WebSocket остается активным для получения данных
            data = await websocket.receive_text()
            print(f"Получено сообщение от клиента: {data}")
    except Exception as e:
        print(f"Возникла ошибка WebSocket {e}")
    finally:
        manager.disconnect(websocket)
        print("Клиент отключился")
