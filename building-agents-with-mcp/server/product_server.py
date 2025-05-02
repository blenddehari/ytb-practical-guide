import asyncio
import uuid
import logging
import os
import json
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directory for storage simulation
STORAGE_DIR = "storage_simulation"
PRODUCTS_FILE = os.path.join(STORAGE_DIR, "products.json")

# Make sure the storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)

# Initialize the products file if it doesn't exist
if not os.path.exists(PRODUCTS_FILE):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump([], f)

app = FastAPI()

# Data models for our product structure
class BaseItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str

class TicketType(BaseItem):
    pass

class TicketCategory(BaseItem):
    pass

class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    price: float
    ticket_type: TicketType
    ticket_category: TicketCategory

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    short_description: str
    long_description: str
    ticket: Ticket

# Define the MCP tool schemas
create_product_schema = {
    "name": "create_product",
    "description": "Create a new product with a ticket",
    "inputSchema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the product"
            },
            "short_description": {
                "type": "string",
                "description": "Short description of the product"
            },
            "long_description": {
                "type": "string",
                "description": "Long description of the product"
            },
            "ticket_price": {
                "type": "number",
                "description": "Price of the ticket"
            },
            "ticket_type": {
                "type": "string",
                "description": "Type of ticket (e.g., Adult, Child, Senior)"
            },
            "ticket_category": {
                "type": "string",
                "description": "Category of ticket (e.g., 1 Day, 2 Day, Weekend)"
            }
        },
        "required": ["title", "short_description", "long_description", "ticket_price", "ticket_type", "ticket_category"]
    }
}

list_products_schema = {
    "name": "list_products",
    "description": "List all existing products",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

# Combined tool schemas
tools = [create_product_schema, list_products_schema]

# In-memory database for demo purposes
ticket_types_db = {
    "adult": TicketType(id="type-1", title="Adult"),
    "child": TicketType(id="type-2", title="Child"),
    "senior": TicketType(id="type-3", title="Senior")
}

ticket_categories_db = {
    "1 day": TicketCategory(id="cat-1", title="1 Day"),
    "2 day": TicketCategory(id="cat-2", title="2 Day"),
    "weekend": TicketCategory(id="cat-3", title="Weekend")
}

# Helper functions for product storage
def load_products():
    """Load products from storage file"""
    try:
        with open(PRODUCTS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_product(product_dict):
    """Save a product to storage file"""
    products = load_products()
    products.append(product_dict)
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=2)

# MCP SSE endpoints
@app.post("/sse")
async def sse_endpoint(request: Request):
    """Handle SSE requests from the MCP client"""
    data = await request.json()
    req_type = data.get("type")
    
    logger.info(f"Received request: {req_type} - {data}")
    
    if req_type == "initialize":
        logger.info("Processing initialize request")
        return {"id": data.get("id"), "type": "initialize.response"}
    
    elif req_type == "list_tools":
        logger.info("Processing list_tools request")
        return {
            "id": data.get("id"),
            "type": "list_tools.response",
            "tools": tools
        }
    
    elif req_type == "call_tool":
        logger.info("Processing call_tool request")
        tool_name = data.get("name")
        tool_input = data.get("input", {})
        
        if tool_name == "create_product":
            result = await create_product(
                title=tool_input.get("title"),
                short_description=tool_input.get("short_description"),
                long_description=tool_input.get("long_description"),
                ticket_price=tool_input.get("ticket_price"),
                ticket_type=tool_input.get("ticket_type"),
                ticket_category=tool_input.get("ticket_category")
            )
            
            return {
                "id": data.get("id"),
                "type": "call_tool.response",
                "content": [{"text": result}]
            }
        
        elif tool_name == "list_products":
            result = await list_products()
            
            return {
                "id": data.get("id"),
                "type": "call_tool.response",
                "content": [{"text": result}]
            }
    
    # Default error response
    logger.warning(f"Unknown request type: {req_type}")
    return {"id": data.get("id"), "type": "error", "error": "Unknown request type"}

async def create_product(
    title: str, 
    short_description: str, 
    long_description: str, 
    ticket_price: float, 
    ticket_type: str, 
    ticket_category: str
) -> str:
    """Create a new product with a ticket"""
    
    # Lowercase and find the closest match in our mock databases
    ticket_type_key = ticket_type.lower()
    ticket_category_key = ticket_category.lower()
    
    # Find or create ticket type
    if ticket_type_key in ticket_types_db:
        type_obj = ticket_types_db[ticket_type_key]
    else:
        type_obj = TicketType(title=ticket_type)
        ticket_types_db[ticket_type_key] = type_obj
    
    # Find or create ticket category
    if ticket_category_key in ticket_categories_db:
        category_obj = ticket_categories_db[ticket_category_key]
    else:
        category_obj = TicketCategory(title=ticket_category)
        ticket_categories_db[ticket_category_key] = category_obj
    
    # Create ticket
    ticket = Ticket(
        price=ticket_price,
        ticket_type=type_obj,
        ticket_category=category_obj
    )
    
    # Create product
    product = Product(
        title=title,
        short_description=short_description,
        long_description=long_description,
        ticket=ticket
    )
    
    # Convert to dict for JSON serialization
    product_dict = product.model_dump()
    
    # Save to our simulated storage
    save_product(product_dict)
    
    return json.dumps(product_dict)

async def list_products() -> str:
    """List all existing products"""
    products = load_products()
    return json.dumps({"products": products})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 