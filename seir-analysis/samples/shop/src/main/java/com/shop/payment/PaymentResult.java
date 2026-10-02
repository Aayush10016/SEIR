package com.shop.payment;

public record PaymentResult(String transactionId, boolean success, String message) {
    public static PaymentResult failed(String message) {
        return new PaymentResult(null, false, message);
    }
}
