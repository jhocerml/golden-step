/*Código para el boton tipo hamburguesa en dispositivos móviles*/

document.addEventListener('DOMContentLoaded', () => {
    const burger = document.querySelector('.burger');
    const navLinks = document.querySelector('.nav-links');

    if (burger) {
        burger.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }
});

/*Código para hacer funcionar el formulario */

const contactForm = document.getElementById('contact-form');
if (contactForm) {
    contactForm.addEventListener('submit', function(event) {
        event.preventDefault(); 

        const submitButton = this.querySelector('button[type="submit"]'); 
        submitButton.classList.add('loading'); 

        const formData = new FormData(this);

        fetch('/send_email', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(data => {
            showFlashMessage('Mensaje enviado correctamente.', 'success');
            this.reset();
            submitButton.classList.remove('loading');
        })
        .catch(error => {
            showFlashMessage('Hubo un error al enviar el mensaje.', 'danger');
            console.error('Error:', error);
            submitButton.classList.remove('loading'); 
        });
    });
}

function showFlashMessage(message, category) {
    const flashContainer = document.getElementById('flash-messages');
    const flashMessage = document.createElement('div');
    flashMessage.className = `alert ${category}`;
    flashMessage.textContent = message;
    flashContainer.appendChild(flashMessage);
    setTimeout(() => {
        flashMessage.remove();
    }, 5000);
}

// ==================
// CARRITO
// ==================

function obtenerCarrito() {
    return JSON.parse(localStorage.getItem('carrito')) || [];
}

function guardarCarrito(carrito) {
    localStorage.setItem('carrito', JSON.stringify(carrito));
    actualizarContador();
}

function actualizarContador() {
    const carrito = obtenerCarrito();
    const total = carrito.reduce((sum, item) => sum + item.cantidad, 0);
    const contador = document.getElementById('cart-count');
    if (contador) contador.textContent = total;
}

// Botones "Agregar al carrito"
document.querySelectorAll('.btn-carrito').forEach(btn => {
    btn.addEventListener('click', () => {
        const nombre = btn.dataset.nombre;
        const precio = parseFloat(btn.dataset.precio);
        const img = btn.dataset.img;

        let carrito = obtenerCarrito();
        const existe = carrito.find(item => item.nombre === nombre);

        if (existe) {
            existe.cantidad += 1;
        } else {
            carrito.push({ nombre, precio, img, cantidad: 1 });
        }

        guardarCarrito(carrito);

        btn.textContent = '✓ Agregado';
        setTimeout(() => btn.textContent = 'Agregar al carrito', 1500);
    });
});

// Si estamos en la página /carrito
if (document.getElementById('carrito-items')) {
    renderizarCarrito();
}

function renderizarCarrito() {
    const carrito = obtenerCarrito();
    const contenedor = document.getElementById('carrito-items');
    const vacio = document.getElementById('carrito-vacio');
    const contenido = document.getElementById('carrito-contenido');

    if (carrito.length === 0) {
        vacio.style.display = 'block';
        contenido.style.display = 'none';
        return;
    }

    vacio.style.display = 'none';
    contenido.style.display = 'flex';

    contenedor.innerHTML = carrito.map((item, index) => `
        <div class="carrito-item">
            <img src="${item.img}" alt="${item.nombre}">
            <div class="carrito-item-info">
                <h3>${item.nombre}</h3>
                <p>s/.${item.precio}</p>
                <div class="carrito-item-controles">
                    <div class="carrito-item-cantidad">
                        <button onclick="cambiarCantidad(${index}, -1)">−</button>
                        <span>${item.cantidad}</span>
                        <button onclick="cambiarCantidad(${index}, 1)">+</button>
                    </div>
                    <p class="carrito-item-subtotal">s/.${item.precio * item.cantidad}</p>
                    <button class="btn-eliminar" onclick="eliminarItem(${index})">✕</button>
                </div>
            </div>
        </div>
    `).join('');

    const subtotal = carrito.reduce((sum, item) => sum + item.precio * item.cantidad, 0);
    document.getElementById('subtotal').textContent = subtotal;
    document.getElementById('total').textContent = subtotal + 0; // Envío gratis
}

function cambiarCantidad(index, cambio) {
    let carrito = obtenerCarrito();
    carrito[index].cantidad += cambio;
    if (carrito[index].cantidad <= 0) carrito.splice(index, 1);
    guardarCarrito(carrito);
    renderizarCarrito();
}

function eliminarItem(index) {
    let carrito = obtenerCarrito();
    carrito.splice(index, 1);
    guardarCarrito(carrito);
    renderizarCarrito();
}

const btnVaciar = document.getElementById('btn-vaciar');
if (btnVaciar) {
    btnVaciar.addEventListener('click', () => {
        localStorage.removeItem('carrito');
        actualizarContador();
        renderizarCarrito();
    });
}

// Actualizar contador al cargar cualquier página
actualizarContador();

// ==================
// CHECKOUT
// ==================

if (document.getElementById('checkout-items')) {
    cargarResumenCheckout();
}

function cargarResumenCheckout() {
    const carrito = obtenerCarrito();
    const contenedor = document.getElementById('checkout-items');

    if (carrito.length === 0) {
        window.location.href = '/carrito';
        return;
    }

    contenedor.innerHTML = carrito.map(item => `
        <div class="checkout-item">
            <img src="${item.img}" alt="${item.nombre}">
            <div>
                <p>${item.nombre}</p>
                <p>x${item.cantidad}</p>
            </div>
            <p>s/.${item.precio * item.cantidad}</p>
        </div>
    `).join('');

    const subtotal = carrito.reduce((sum, item) => sum + item.precio * item.cantidad, 0);
    document.getElementById('checkout-subtotal').textContent = 's/.' + subtotal;
    document.getElementById('checkout-total').textContent = 's/.' + (subtotal + 10);
}

const checkoutForm = document.getElementById('checkout-form');
if (checkoutForm) {
    checkoutForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const carrito = obtenerCarrito();
        const subtotal = carrito.reduce((sum, item) => sum + item.precio * item.cantidad, 0);

        const pedido = {
            nombre: document.getElementById('nombre').value,
            telefono: document.getElementById('telefono').value,
            direccion: document.getElementById('direccion').value,
            ciudad: document.getElementById('ciudad').value,
            referencia: document.getElementById('referencia').value,
            productos: carrito,
            total: subtotal + 10
        };

        fetch('/guardar_pedido', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(pedido)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                localStorage.removeItem('carrito');
                actualizarContador();
                document.querySelector('.checkout-page').style.display = 'none';
                document.getElementById('checkout-exito').style.display = 'flex';
            }
        })
        .catch(error => console.error('Error:', error));
    });
}