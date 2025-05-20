from . import virtual_sensor

def get_product_registry():
    """
    Get a mapping of product names to their corresponding modules.
    """
    product_registry = {}

    # Register virtual sensor product
    product_registry[virtual_sensor.get_product_name()] = virtual_sensor

    return product_registry
