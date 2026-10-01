package com.shop.api;

import com.shop.billing.Invoice;
import com.shop.model.Order;
import com.shop.order.OrderService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/orders")
public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping("/checkout")
    public Invoice checkout(@RequestBody Order order) {
        return orderService.checkout(order);
    }
}
