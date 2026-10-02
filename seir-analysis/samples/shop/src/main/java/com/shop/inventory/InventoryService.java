package com.shop.inventory;

import com.shop.model.Order;
import java.util.HashMap;
import java.util.Map;

public class InventoryService {
    private final Map<String, Integer> stock = new HashMap<>();

    public boolean reserve(Order order) {
        for (Order.LineItem item : order.items()) {
            if (stock.getOrDefault(item.sku(), 0) < item.quantity()) {
                return false;
            }
        }
        return true;
    }
}
