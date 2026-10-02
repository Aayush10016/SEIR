package com.shop.api;

import com.shop.model.Order;
import com.shop.payment.PaymentResult;
import com.shop.payment.PaymentService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/payments")
public class PaymentController {
    private final PaymentService paymentService;

    public PaymentController(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    @PostMapping("/{orderId}")
    public PaymentResult pay(@RequestBody Order order) {
        return paymentService.pay(order);
    }

    @PostMapping("/{txId}/refund")
    public PaymentResult refund(@PathVariable String txId) {
        return paymentService.refund(txId);
    }
}
