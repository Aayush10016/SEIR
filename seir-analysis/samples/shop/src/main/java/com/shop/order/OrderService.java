package com.shop.order;

import com.shop.billing.Invoice;
import com.shop.billing.InvoiceService;
import com.shop.inventory.InventoryService;
import com.shop.model.*;
import com.shop.notify.NotificationService;
import com.shop.payment.PaymentResult;
import com.shop.payment.PaymentService;

public class OrderService {
    private final PaymentService payments;
    private final InventoryService inventory;
    private final InvoiceService invoices = new InvoiceService();
    private NotificationService notifications;

    public OrderService(PaymentService payments, InventoryService inventory) {
        this.payments = payments;
        this.inventory = inventory;
    }

    public void setNotifications(NotificationService notifications) {
        this.notifications = notifications;
    }

    public Invoice checkout(Order order) {
        if (!inventory.reserve(order)) {
            throw new IllegalStateException("out of stock");
        }
        PaymentResult result = payments.pay(order);
        order.markPaid();
        var invoice = invoices.issue(order, result);
        notifications.orderPaid(order);
        return invoice;
    }

    public Order.Status statusOf(Order order) {
        return order.status();
    }
}
