package com.shop.payment;

import com.shop.model.Money;
import com.shop.model.Order;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class PaymentService {
    private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

    private final PaymentGateway gateway;
    private final LegacyPaymentService legacy;

    @Autowired
    public PaymentService(PaymentGateway gateway, LegacyPaymentService legacy) {
        this.gateway = gateway;
        this.legacy = legacy;
    }

    public PaymentResult pay(Order order) {
        Money total = order.total();
        PaymentResult result = gateway.charge(order.customer().email(), total);
        if (!result.success()) {
            log.warn("Primary gateway failed, falling back to legacy: {}", result.message());
            result = this.legacy.charge(order.customer().email(), total);
        }
        return result;
    }

    public PaymentResult refund(String transactionId) {
        return PaymentResult.failed("refunds not supported for " + transactionId);
    }
}
