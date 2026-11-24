
// ============================================
// SAI ELECTRONICS - COMPLETE FRONTEND
// ============================================

const API_URL =
    "https://mb3sdj990a.execute-api.us-east-1.amazonaws.com";

const UPI_ID = "8106576346@sbi";
const PAYEE_NAME = "Sugur Sai Vardhan";

let products = [];
let cart = [];
let currentCustomer = null;
let pendingPayment = null;

// ============================================
// HTML ELEMENTS
// ============================================

const $ = (id) => document.getElementById(id);

const productGrid = $("product-grid");
const cartCount = $("cart-count");
const cartButton = $("cart-button");
const showLoginButton = $("show-login");
const customerStatus = $("customer-status");

const accountSection = $("account");
const accountMessage = $("account-message");
const registerForm = $("register-form");
const loginForm = $("login-form");

const myOrdersButton = $("my-orders-button");
const myOrdersSection = $("my-orders-section");
const ordersList = $("orders-list");
const ordersMessage = $("orders-message");

const paymentSection = $("payment-section");
const paymentForm = $("payment-form");
const paymentMessage = $("payment-message");
const paymentReferenceInput = $("payment-reference");
const paymentOrderDetails = $("payment-order-details");
const upiQr = $("upi-qr");
const upiPayLink = $("upi-pay-link");
const submitPaymentButton = $("submit-payment-button");


// ============================================
// API REQUEST
// ============================================

async function apiRequest(endpoint, options = {}) {

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error("Invalid server response.");
    }

    if (!response.ok || data.success === false) {
        throw new Error(
            data.message || `Server error: ${response.status}`
        );
    }

    return data;
}


// ============================================
// SAFE HTML ELEMENT CREATION
// ============================================

function createElement(tag, text = "", className = "") {

    const element = document.createElement(tag);

    element.textContent = text;

    if (className) {
        element.className = className;
    }

    return element;
}


// ============================================
// CUSTOMER ACCOUNT
// ============================================

function showAccount(mode = "login") {

    if (myOrdersSection) myOrdersSection.hidden = true;
    if (paymentSection) paymentSection.hidden = true;

    accountSection.hidden = false;
    accountMessage.textContent = "";

    const registering = mode === "register";

    registerForm.hidden = !registering;
    loginForm.hidden = registering;

    $("account-title").textContent =
        registering ? "Create Your Account" : "Customer Login";

    accountSection.scrollIntoView({ behavior: "smooth" });
}


function updateCustomerStatus() {

    if (currentCustomer) {

        customerStatus.textContent =
            `Hello, ${currentCustomer.name}`;

        showLoginButton.textContent = "Logout";
        myOrdersButton.hidden = false;

    } else {

        customerStatus.textContent = "";

        showLoginButton.textContent = "Login / Register";

        myOrdersButton.hidden = true;

        if (myOrdersSection) myOrdersSection.hidden = true;
        if (paymentSection) paymentSection.hidden = true;
    }
}


// ============================================
// REGISTER
// ============================================

registerForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    const name = $("register-name").value.trim();
    const email = $("register-email").value.trim();
    const password = $("register-password").value;

    accountMessage.textContent = "Creating account...";

    try {

        const result = await apiRequest("/register", {
            method: "POST",
            body: JSON.stringify({
                name,
                email,
                password
            })
        });

        accountMessage.textContent =
            `${result.message}. Please log in.`;

        registerForm.reset();

        $("login-email").value = email;

        registerForm.hidden = true;
        loginForm.hidden = false;

        $("account-title").textContent = "Customer Login";

    } catch (error) {

        accountMessage.textContent = error.message;
    }
});


// ============================================
// LOGIN
// ============================================

loginForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    const email = $("login-email").value.trim();
    const password = $("login-password").value;

    accountMessage.textContent = "Logging in...";

    try {

        const result = await apiRequest("/login", {
            method: "POST",
            body: JSON.stringify({
                email,
                password
            })
        });

        if (!result.customer || !result.customer.id) {
            throw new Error("Customer information not received.");
        }

        currentCustomer = {
            id: result.customer.id,
            name: result.customer.name
        };

        updateCustomerStatus();

        loginForm.reset();

        accountMessage.textContent = "Login successful!";

        setTimeout(() => {
            accountSection.hidden = true;
            accountMessage.textContent = "";
        }, 700);

    } catch (error) {

        accountMessage.textContent = error.message;
    }
});


// ============================================
// LOGOUT AND ACCOUNT BUTTONS
// ============================================

showLoginButton.addEventListener("click", () => {

    if (!currentCustomer) {
        showAccount("login");
        return;
    }

    if (!confirm("Are you sure you want to logout?")) {
        return;
    }

    currentCustomer = null;
    cart = [];
    pendingPayment = null;

    updateCartCount();
    updateCustomerStatus();

    accountSection.hidden = true;

    alert("You have logged out.");
});

$("register-tab").addEventListener("click", () => {
    showAccount("register");
});

$("login-tab").addEventListener("click", () => {
    showAccount("login");
});

$("close-account").addEventListener("click", () => {
    accountSection.hidden = true;
});


// ============================================
// LOAD PRODUCTS FROM AURORA THROUGH LAMBDA
// ============================================

async function loadProducts() {

    productGrid.replaceChildren();

    productGrid.textContent = "Loading products...";

    try {

        const result = await apiRequest("/products");

        products = Array.isArray(result.products)
            ? result.products
            : [];

        displayProducts();

    } catch (error) {

        productGrid.textContent =
            `Unable to load products: ${error.message}`;

        console.error("Products API error:", error);
    }
}


// ============================================
// DISPLAY PRODUCT IMAGES AND DETAILS
// ============================================

function displayProducts() {

    productGrid.replaceChildren();

    if (products.length === 0) {

        productGrid.textContent = "No products available.";

        return;
    }

    products.forEach((product) => {

        const card = createElement("div", "", "product-card");

        // Product image area
        const imageBox = createElement(
            "div",
            "",
            "product-image-container"
        );

        Object.assign(imageBox.style, {
            width: "100%",
            height: "210px",
            background: "#f4f4f4",
            borderRadius: "10px",
            overflow: "hidden",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "15px"
        });

        const image = document.createElement("img");

        image.alt = product.name || "Electronics product";
        image.loading = "lazy";

        Object.assign(image.style, {
            width: "100%",
            height: "100%",
            objectFit: "contain",
            padding: "8px"
        });

        // Use actual URL returned by Lambda
        if (product.image_url) {

            image.src = product.image_url;

        } else {

            imageBox.textContent = "Image unavailable";
        }

        // Show fallback if image fails
        image.onerror = () => {

            imageBox.replaceChildren();

            imageBox.textContent = "📦";

            imageBox.style.fontSize = "55px";
        };

        imageBox.appendChild(image);

        // Product information
        const name = createElement(
            "h3",
            product.name || "Electronics"
        );

        const category = createElement(
            "p",
            product.category || "Electronics"
        );

        const price = createElement(
            "p",
            `₹${Number(product.price).toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}`
        );

        const stockValue = Number(product.stock);

        const stock = createElement(
            "p",
            stockValue > 0
                ? `Available: ${stockValue}`
                : "Out of stock"
        );

        const button = createElement(
            "button",
            "Add to Cart",
            "shop-btn"
        );

        button.type = "button";
        button.disabled = stockValue <= 0;

        button.addEventListener("click", () => {
            addToCart(product);
        });

        card.append(
            imageBox,
            name,
            category,
            price,
            stock,
            button
        );

        productGrid.appendChild(card);
    });
}


// ============================================
// SHOPPING CART
// ============================================

function addToCart(product) {

    const existing = cart.find(
        item => Number(item.id) === Number(product.id)
    );

    const currentQuantity = existing
        ? existing.quantity
        : 0;

    if (currentQuantity >= Number(product.stock)) {

        alert("Available stock limit reached.");

        return;
    }

    if (existing) {

        existing.quantity++;

    } else {

        cart.push({
            ...product,
            quantity: 1
        });
    }

    updateCartCount();

    alert(`${product.name} added to cart!`);
}


function updateCartCount() {

    const total = cart.reduce(
        (sum, item) => sum + item.quantity,
        0
    );

    cartCount.textContent = total;
}


// ============================================
// CHECKOUT - CREATE ORDER
// ============================================

async function showCart() {

    if (cart.length === 0) {

        alert("Your cart is empty.");

        return;
    }

    if (!currentCustomer) {

        alert("Please login before placing an order.");

        showAccount("login");

        return;
    }

    const total = cart.reduce(
        (sum, item) =>
            sum + Number(item.price) * item.quantity,
        0
    );

    const summary = cart.map(item => {

        const itemTotal =
            Number(item.price) * item.quantity;

        return `${item.name} x ${item.quantity} = ₹${itemTotal.toFixed(2)}`;

    }).join("\n");

    const confirmed = confirm(
        `YOUR SHOPPING CART\n\n${summary}\n\n` +
        `Total: ₹${total.toFixed(2)}\n\n` +
        `Place order and continue to UPI payment?`
    );

    if (!confirmed) return;

    cartButton.disabled = true;

    try {

        const items = cart.map(item => ({
            product_id: Number(item.id),
            quantity: Number(item.quantity)
        }));

        const result = await apiRequest("/orders", {
            method: "POST",
            body: JSON.stringify({
                customer_id: currentCustomer.id,
                items
            })
        });

        pendingPayment = {
            orderId: result.order_id,
            customerId: currentCustomer.id,
            amount: Number(result.total_amount)
        };

        cart = [];

        updateCartCount();

        await loadProducts();

        showPaymentSection();

    } catch (error) {

        alert("Order creation failed: " + error.message);

    } finally {

        cartButton.disabled = false;
    }
}

cartButton.addEventListener("click", showCart);


// ============================================
// UPI QR CODE GENERATION
// ============================================

function showPaymentSection() {

    if (!pendingPayment) return;

    accountSection.hidden = true;
    myOrdersSection.hidden = true;
    paymentSection.hidden = false;

    paymentForm.reset();

    paymentMessage.textContent = "";

    submitPaymentButton.disabled = false;

    const amount = pendingPayment.amount.toFixed(2);

    const note =
        `SAI ELECTRONICS Order ${pendingPayment.orderId}`;

    const upiUrl =
        "upi://pay" +
        `?pa=${encodeURIComponent(UPI_ID)}` +
        `&pn=${encodeURIComponent(PAYEE_NAME)}` +
        `&am=${encodeURIComponent(amount)}` +
        "&cu=INR" +
        `&tn=${encodeURIComponent(note)}`;

    paymentOrderDetails.textContent =
        `Order #${pendingPayment.orderId} | Amount: ₹${amount}`;

    $("upi-id-display").textContent = UPI_ID;

    upiPayLink.href = upiUrl;

    upiQr.replaceChildren();

    if (typeof QRCode === "undefined") {

        paymentMessage.textContent =
            "QR library unavailable. Refresh the page and try again.";

        return;
    }

    new QRCode(upiQr, {
        text: upiUrl,
        width: 240,
        height: 240,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.M
    });

    paymentSection.scrollIntoView({
        behavior: "smooth"
    });
}


// ============================================
// SUBMIT UPI TRANSACTION REFERENCE
// ============================================

paymentForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    if (!currentCustomer || !pendingPayment) {

        paymentMessage.textContent =
            "No active order available for payment submission.";

        return;
    }

    const reference =
        paymentReferenceInput.value.trim();

    if (reference.length < 6 || reference.length > 100) {

        paymentMessage.textContent =
            "Enter a valid UPI transaction reference.";

        return;
    }

    submitPaymentButton.disabled = true;

    paymentMessage.textContent =
        "Submitting payment reference...";

    try {

        const result = await apiRequest("/submit-payment", {
            method: "POST",
            body: JSON.stringify({
                customer_id: pendingPayment.customerId,
                order_id: pendingPayment.orderId,
                payment_reference: reference
            })
        });

        paymentMessage.textContent =
            result.message ||
            "Payment reference submitted. Awaiting verification.";

        paymentForm.reset();

        pendingPayment = null;

        paymentSection.hidden = true;

        await showMyOrders();

    } catch (error) {

        paymentMessage.textContent =
            "Payment submission failed: " + error.message;

        submitPaymentButton.disabled = false;
    }
});


// ============================================
// CLOSE PAYMENT SECTION
// ============================================

$("close-payment").addEventListener("click", () => {

    paymentSection.hidden = true;

});


// ============================================
// MY ORDERS
// ============================================

async function showMyOrders() {

    if (!currentCustomer) {

        alert("Please login to view your orders.");

        showAccount("login");

        return;
    }

    accountSection.hidden = true;
    paymentSection.hidden = true;
    myOrdersSection.hidden = false;

    myOrdersSection.scrollIntoView({
        behavior: "smooth"
    });

    await loadMyOrders();
}


// ============================================
// LOAD CUSTOMER ORDERS
// ============================================

async function loadMyOrders() {

    if (!currentCustomer) return;

    ordersMessage.textContent = "Loading your orders...";

    ordersList.replaceChildren();

    try {

        const result = await apiRequest(
            `/my-orders?customer_id=${encodeURIComponent(currentCustomer.id)}`
        );

        const orders = Array.isArray(result.orders)
            ? result.orders
            : [];

        if (orders.length === 0) {

            ordersMessage.textContent =
                "You have not placed any orders yet.";

            return;
        }

        ordersMessage.textContent =
            `Found ${orders.length} order(s).`;

        orders.forEach(order => {

            const card = createElement(
                "div",
                "",
                "order-card"
            );

            const title = createElement(
                "h3",
                `Order #${order.order_id}`
            );

            const amount = createElement(
                "p",
                `Total Amount: ₹${Number(order.total_amount).toFixed(2)}`
            );

            const status = createElement(
                "p",
                `Order Status: ${order.order_status}`,
                "order-status"
            );

            const paymentStatus = createElement(
                "p",
                `Payment Status: ${order.payment_status}`
            );

            const date = createElement(
                "p",
                `Order Date: ${order.created_at}`
            );

            card.append(
                title,
                amount,
                status,
                paymentStatus,
                date
            );

            const itemsHeading = createElement(
                "h4",
                "Products"
            );

            card.appendChild(itemsHeading);

            (order.items || []).forEach(item => {

                const itemElement = createElement(
                    "div",
                    `${item.product_name} | Quantity: ${item.quantity} | Price: ₹${Number(item.price).toFixed(2)}`,
                    "order-item"
                );

                card.appendChild(itemElement);
            });

            ordersList.appendChild(card);
        });

    } catch (error) {

        ordersMessage.textContent =
            "Unable to load orders: " + error.message;
    }
}


// ============================================
// MY ORDERS BUTTONS
// ============================================

myOrdersButton.addEventListener("click", showMyOrders);

$("refresh-orders").addEventListener("click", loadMyOrders);

$("close-orders").addEventListener("click", () => {

    myOrdersSection.hidden = true;

    $("products").scrollIntoView({
        behavior: "smooth"
    });
});


// ============================================
// INITIALIZE WEBSITE
// ============================================

updateCustomerStatus();

loadProducts();
