package com.shop.notify;

import com.shop.model.Order;
import com.shop.order.OrderService;

public class NotificationService {
    private final OrderService orders;

    public NotificationService(OrderService orders) {
        this.orders = orders;
    }

    public void orderPaid(Order order) {
        System.out.println("Order " + order.id() + " is now " + orders.statusOf(order));
    }
}
