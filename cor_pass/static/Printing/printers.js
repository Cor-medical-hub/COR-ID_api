
async function printLabel(printerIp, templateNumber, content, resultElement = null) {
    if (resultElement) {
        resultElement.textContent = 'Отправка задания на печать...';
        resultElement.style.color = 'black';
    }
    
    const requestData = {
        printer_ip: printerIp,
        labels: [
            {
                model_id: templateNumber,
                content: content,
                uuid: Date.now().toString()  
            }
        ]
    };

    try {
        const response = await fetch('/api/print_labels', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + getToken()
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Unknown error');
        }

        const result = await response.json();
        console.log('Печать успешна:', result);
        
        if (resultElement) {
            resultElement.textContent = `Задание отправлено (IP: ${printerIp}, Шаблон: ${templateNumber})`;
            resultElement.style.color = 'green';
        }
        
        return result;
    } catch (error) {
        console.error('Ошибка:', error);
        
        if (resultElement) {
            resultElement.textContent = 'Ошибка при печати: ' + error.message;
            resultElement.style.color = 'red';
        }
        
        throw error;
    }
}



    // Функция проверки доступности принтера
    async function checkPrinterAvailability(ip = PRINTER_IP) {
        try {
            console.log(`[checkPrinterAvailability] Проверка IP: ${ip}`);
            const response = await fetch(`/api/check_printer?ip=${encodeURIComponent(ip)}`);
            console.log(`[checkPrinterAvailability] HTTP статус: ${response.status}`);

            const data = await response.json();
            console.log(`[checkPrinterAvailability] Ответ от сервера:`, data);

            return data.available;
        } catch (error) {
            console.error('[checkPrinterAvailability] Ошибка запроса:', error);
            return false;
        }
    }
    
 

// Функция мониторинга состояния всех принтеров
function startPrinterMonitoring() {
    const statusElement = document.getElementById('printerStatus');
    if (!statusElement) return;

    let currentPrinterIndex = 0;
    
    // Функция для проверки одного принтера
    const checkNextPrinter = async () => {
        if (availablePrinters.length === 0) {
            return;
        }

        // Получаем текущий принтер (с циклическим перебором)
        const printer = availablePrinters[currentPrinterIndex];
        currentPrinterIndex = (currentPrinterIndex + 1) % availablePrinters.length;

        // Находим строку таблицы для этого принтера
        const row = document.querySelector(`tr[data-device-id="${printer.id}"]`);
        if (!row) return;

        // Находим индикатор статуса
        const statusIndicator = row.querySelector('.status-indicator');
        if (!statusIndicator) return;

        try {
            const isAvailable = await checkPrinterAvailability(printer.ip_address);
            
            // Сохраняем статус
            printerStatuses[printer.ip_address] = {
                available: isAvailable,
                lastChecked: new Date()
            };
            
            // Обновляем индикатор
            statusIndicator.style.backgroundColor = isAvailable ? 'green' : 'red';
            statusIndicator.title = `${printer.device_class} (${printer.ip_address})\n` +
                                  `Статус: ${isAvailable ? 'Доступен' : 'Недоступен'}\n` +
                                  `Последняя проверка: ${new Date().toLocaleTimeString()}`;
            
        } catch (error) {
            console.error(`Ошибка проверки принтера ${printer.ip_address}:`, error);
            statusIndicator.style.backgroundColor = 'orange';
            statusIndicator.title = `Ошибка проверки ${printer.ip_address}: ${error.message}`;
        }
    };

    // Запускаем проверку с интервалом
    const intervalId = setInterval(checkNextPrinter, 1000);
    
    // Возвращаем функцию для остановки мониторинга
    return () => clearInterval(intervalId);
}

    // Функция добавления нового устройства
    async function addDevice() {
        const resultElement = document.getElementById('addDeviceResult');
        resultElement.textContent = '';
        
        // Получаем значения из полей формы
        const deviceType = document.getElementById('deviceType').value;
        const deviceId = document.getElementById('deviceId').value;
        const deviceIp = document.getElementById('deviceIp').value;
        const deviceLocation = document.getElementById('deviceLocation').value;
        const deviceInfo = document.getElementById('deviceInformation').value;


        // Проверяем обязательные поля
        if (!deviceType || !deviceId || !deviceIp) {
            resultElement.textContent = 'Пожалуйста, заполните все обязательные поля';
            resultElement.style.color = 'red';
            return;
        }

        // Проверяем валидность ID устройства
        const idNumber = parseInt(deviceId);
        if (isNaN(idNumber) || idNumber < 0 || idNumber > 65535) {
            resultElement.textContent = 'ID устройства должен быть числом от 0 до 65535';
            resultElement.style.color = 'red';
            return;
        }

        // Подготавливаем данные для отправки
        const deviceData = {
            device_class: deviceType,
            device_identifier: deviceId,
            ip_address: deviceIp,
            subnet_mask: "255.255.255.0", // По умолчанию
            gateway: "0.0.0.0", // По умолчанию
            port: 0, // По умолчанию
            comment: deviceInfo || "", 
            location: deviceLocation || "" // Если не указано - пустая строка
        };

        try {
            resultElement.textContent = 'Добавление устройства...';
            resultElement.style.color = 'black';
            
            // Отправляем запрос на сервер
            const response = await fetch('/api/printing_devices/', {
                method: 'POST',
                headers: {
                    'accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                },
                body: JSON.stringify(deviceData)
            });

            if (!response.ok) {
                throw new Error(`Ошибка HTTP: ${response.status}`);
            }

            const result = await response.json();
            console.log('Устройство успешно добавлено:', result);
            resultElement.textContent = 'Устройство успешно добавлено!';
            resultElement.style.color = 'green';
            
            // Очищаем форму
            document.getElementById('deviceType').value = '';
            document.getElementById('deviceId').value = '';
            document.getElementById('deviceIp').value = '';
            document.getElementById('deviceLocation').value = '';
            
            // Закрываем модальное окно через 2 секунды
            setTimeout(() => {
                document.getElementById('addDeviceModal').style.display = 'none';
            }, 2000);
            
        } catch (error) {
            console.error('Ошибка при добавлении устройства:', error);
            resultElement.textContent = 'Произошла ошибка при добавлении устройства: ' + error.message;
            resultElement.style.color = 'red';
        }
    }



// Обновленная функция loadDevicesList
async function loadDevicesList() {
    const devicesListElement = document.getElementById('devicesList');
    if (!devicesListElement) return;

    try {
        devicesListElement.innerHTML = '<p>Загрузка списка устройств...</p>';
        
        const response = await fetch('/api/printing_devices/all', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + getToken()
            }
        });
        
        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }
        
        const devices = await response.json();
        availablePrinters = devices.filter(device => 
            device.device_class === 'GlassPrinter' || 
            device.device_class === 'CassetPrinter' ||
            device.device_class === 'CassetPrinterHopper'
        );
        
        updatePrinterDropdown();
        
        let tableHTML = `
            <table class="devices-table">
                <thead>
                    <tr>
                        <th>Тип</th>
                        <th>Идентификатор</th>
                        <th>IP-адрес</th>
                        <th>Местоположение</th>
                        <th>Комментарий</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        devices.forEach(device => {
            const lastStatus = printerStatuses[device.ip_address];
            const statusColor = lastStatus ? 
                (lastStatus.available ? 'green' : 'red') : 'gray';
            
            tableHTML += `
                <tr data-device-id="${device.id}">
                    <td>${device.device_class}</td>
                    <td>${device.device_identifier}</td>
                    <td><input type="text" class="editable-field ip-address" value="${device.ip_address}" data-original="${device.ip_address}"></td>
                    <td><input type="text" class="editable-field location" value="${device.location || ''}" data-original="${device.location || ''}"></td>
                    <td><input type="text" class="editable-field comment" value="${device.comment || ''}" data-original="${device.comment || ''}"></td>
                    <td class="actions">
                       
                        <button class="action-btn save-btn" onclick="saveDeviceChanges('${device.id}')" title="Сохранить">💾</button>
                        <button class="action-btn delete-btn" onclick="deleteDevice('${device.id}')" title="Удалить">❌</button>
                         <div class="status-indicator" style="background-color: ${statusColor}" 
                             title="${lastStatus ? `Статус: ${lastStatus.available ? 'Доступен' : 'Недоступен'}\nПоследняя проверка: ${lastStatus.lastChecked.toLocaleTimeString()}` : 'Статус неизвестен'}"></div>
                    </td>
                </tr>
            `;
        });
        
        tableHTML += `
                </tbody>
            </table>
        `;
        
        devicesListElement.innerHTML = tableHTML;
        
        return devices;
    } catch (error) {
        console.error('Ошибка при загрузке списка устройств:', error);
        devicesListElement.innerHTML = `<p style="color: red;">Ошибка при загрузке: ${error.message}</p>`;
        throw error;
    }
}

// Функция для сохранения изменений устройства
async function saveDeviceChanges(deviceId) {
    const row = document.querySelector(`tr[data-device-id="${deviceId}"]`);
    if (!row) return;

    // Получаем все необходимые данные из строки таблицы
    const deviceClass = row.querySelector('td:first-child').textContent;
    const deviceIdentifier = row.querySelector('td:nth-child(2)').textContent;
    const ipAddress = row.querySelector('.ip-address').value;
    const location = row.querySelector('.location').value;
    const comment = row.querySelector('.comment').value;

    // Формируем полный объект данных согласно API
    const deviceData = {
        device_class: deviceClass,
        device_identifier: deviceIdentifier,
        ip_address: ipAddress,
        subnet_mask: "255.255.255.0", // Значение по умолчанию
        gateway: "0.0.0.0", // Значение по умолчанию
        port: 0, // Значение по умолчанию
        comment: comment,
        location: location
    };

    try {
        const response = await fetch(`/api/printing_devices/${deviceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + getToken()
            },
            body: JSON.stringify(deviceData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Ошибка HTTP: ${response.status}`);
        }

        const result = await response.json();
        console.log('Устройство успешно обновлено:', result);

        // Обновляем оригинальные значения в data-атрибутах
        row.querySelector('.ip-address').dataset.original = ipAddress;
        row.querySelector('.location').dataset.original = location;
        row.querySelector('.comment').dataset.original = comment;

        // Показываем уведомление вместо alert
        showNotification('Изменения успешно сохранены!', 'success');
        updatePrinterDropdown(); // Обновляем список принтеров

    } catch (error) {
        console.error('Ошибка при сохранении изменений:', error);
        
        // Показываем более информативное сообщение об ошибке
        let errorMessage = 'Ошибка при сохранении: ';
        if (error.message.includes('422')) {
            errorMessage += 'Неверные данные. Проверьте введенные значения.';
        } else {
            errorMessage += error.message;
        }
        
        showNotification(errorMessage, 'error');
        
        // Восстанавливаем оригинальные значения
        row.querySelector('.ip-address').value = row.querySelector('.ip-address').dataset.original;
        row.querySelector('.location').value = row.querySelector('.location').dataset.original;
        row.querySelector('.comment').value = row.querySelector('.comment').dataset.original;
    }
}

// Вспомогательная функция для показа уведомлений
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Автоматическое скрытие через 3 секунды
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 3000);
}

// Функция для удаления устройства
async function deleteDevice(deviceId) {
    if (!confirm('Вы уверены, что хотите удалить это устройство?')) {
        return;
    }

    try {
        const response = await fetch(`/api/printing_devices/${deviceId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            }
        });

        console.log("Ответ:",response);
        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        // Удаляем строку из таблицы
        document.querySelector(`tr[data-device-id="${deviceId}"]`).remove();
        alert('Устройство успешно удалено!');
        updatePrinterDropdown(); // Обновляем список принтеров
        loadDevicesList();
    } catch (error) {
        console.error('Ошибка при удалении устройства:', error);
        alert('Ошибка при удалении: ' + error.message);
    }
}

function updatePrinterDropdown() {
    const printerDropdown = document.getElementById('printerIp');
    const customIpInput = document.getElementById('customPrinterIp');
    if (!printerDropdown) return;

    // Проверяем, что availablePrinters существует и является массивом
    if (!Array.isArray(availablePrinters)) {
        console.error('availablePrinters is not an array:', availablePrinters);
        availablePrinters = [];
    }

    // Сохраняем текущее значение
    const currentValue = printerDropdown.value === 'custom' ? customIpInput.value : printerDropdown.value;
    
    // Очищаем и заполняем заново
    printerDropdown.innerHTML = '';
    
    // Добавляем все принтеры
    if (availablePrinters.length > 0) {
        console.log('Adding printers to dropdown:', availablePrinters);
        availablePrinters.forEach(printer => {
            const option = document.createElement('option');
            option.value = printer.ip_address;
            option.textContent = `${printer.ip_address}${printer.location ? ` (${printer.location})` : ''}`;
            printerDropdown.appendChild(option);
        });
        
        // Добавляем разделитель
        const divider = document.createElement('option');
        divider.disabled = true;
        divider.textContent = '──────────';
        printerDropdown.appendChild(divider);
    }
    
    // Добавляем опцию для ввода своего IP
    const customOption = document.createElement('option');
    customOption.value = 'custom';
    customOption.textContent = 'Ввести свой IP';
    printerDropdown.appendChild(customOption);
    
    // Восстанавливаем выбранное значение
    if (currentValue) {
        if (availablePrinters.some(p => p.ip_address === currentValue)) {
            printerDropdown.value = currentValue;
            customIpInput.style.display = 'none';
        } else {
            printerDropdown.value = 'custom';
            customIpInput.value = currentValue;
            customIpInput.style.display = 'inline';
        }
    } else if (availablePrinters.length > 0) {
        // Устанавливаем первый принтер по умолчанию
        printerDropdown.value = availablePrinters[0].ip_address;
    }
    
    // Обработчик изменения выбора
    printerDropdown.addEventListener('change', function() {
        if (this.value === 'custom') {
            customIpInput.style.display = 'inline';
            customIpInput.focus();
        } else {
            customIpInput.style.display = 'none';
        }
    });
    
    // Обработчик ввода своего IP
    customIpInput.addEventListener('input', function() {
        // Можно добавить валидацию IP здесь
    });
}

// Обработчик для модального окна теста
document.getElementById('sendLabelButton').addEventListener('click', async () => {
    const testResult = document.getElementById('testResult');
    
    // Получаем значения из полей формы
    const printerIpSelect = document.getElementById('printerIp');
    const customIpInput = document.getElementById('customPrinterIp');
    const printerIp = printerIpSelect.value === 'custom' 
        ? customIpInput.value.trim() 
        : printerIpSelect.value.trim();
    const templateId = document.getElementById('template').value;
    const clinicId = document.getElementById('clinicId').value.trim();
    const caseCode = document.getElementById('caseCode').value.trim();
    const sampleNumber = document.getElementById('sampleNumber').value.trim();
    const cassetteNumber = document.getElementById('cassetteNumber').value.trim();
    const glassNumber = document.getElementById('glassNumber').value.trim();
    const staining = document.getElementById('staining').value.trim();
    const hopperNumber = document.getElementById('hopperNumber').value.trim();
    const patientCorId = document.getElementById('patientCorId').value.trim();
    const hopperID= 3;
    
    // Проверка обязательных полей
    if (!printerIp) {
        testResult.textContent = 'Ошибка: Не указан IP-адрес принтера';
        testResult.style.color = 'red';
        return;
    }
    
    // Проверка валидности номера шаблона
    const templateNumber = parseInt(templateId);
    if (isNaN(templateNumber) || templateNumber < 0 || templateNumber > 65535) {
        testResult.textContent = 'Ошибка: Номер шаблона должен быть числом от 0 до 65535';
        testResult.style.color = 'red';
        return;
    }

    // Формируем строку content из всех параметров
    const content = [
        hopperID,
        clinicId,
        caseCode,
        sampleNumber,
        cassetteNumber,
        glassNumber,
        staining,
        hopperNumber,
        patientCorId
    ].join('|');

    // Используем универсальную функцию печати
    await printLabel(printerIp, templateNumber, content, testResult);
});