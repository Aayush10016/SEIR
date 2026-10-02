package com.shop.billing;

import com.shop.model.Money;

public record Invoice(String orderId, String transactionId, Money total) {}
