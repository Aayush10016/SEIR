package com.shop.billing;

import com.shop.model.Order;
import com.shop.payment.PaymentResult;

public class InvoiceService {
    public Invoice issue(Order order, PaymentResult payment) {
        if (!payment.success()) {
            throw new IllegalStateException("cannot invoice unpaid order");
        }
        return new Invoice(order.id(), payment.transactionId(), order.total());
    }
}
