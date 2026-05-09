CREATE TABLE roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255)
);

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(128) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role_id INT NOT NULL,
  active BOOL DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE TABLE articulos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku VARCHAR(128) NOT NULL UNIQUE,
  descripcion VARCHAR(255) NOT NULL,
  division VARCHAR(120),
  calibre VARCHAR(120),
  unidades_por_bulto INT NOT NULL DEFAULT 1,
  bultos_por_pallet INT NOT NULL DEFAULT 1,
  activo BOOL DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE lotes_procesamiento (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(255) NOT NULL,
  fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
  origen VARCHAR(255),
  estado VARCHAR(80) NOT NULL DEFAULT 'pendiente'
);

CREATE TABLE archivos_subidos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  batch_id INT,
  filename VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255),
  category VARCHAR(80) NOT NULL,
  content_type VARCHAR(120),
  size_bytes INT NOT NULL DEFAULT 0,
  checksum_sha256 VARCHAR(64) NOT NULL,
  data LONGBLOB NOT NULL,
  status VARCHAR(80) NOT NULL DEFAULT 'recibido',
  error_message TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME,
  FOREIGN KEY (batch_id) REFERENCES lotes_procesamiento(id)
);

CREATE TABLE consolidados (
  id INT AUTO_INCREMENT PRIMARY KEY,
  batch_id INT NOT NULL,
  uploaded_file_id INT,
  filename VARCHAR(255) NOT NULL,
  reparto VARCHAR(120),
  camion VARCHAR(120),
  chofer VARCHAR(120),
  deposito VARCHAR(120),
  cancha VARCHAR(120),
  almacen VARCHAR(120),
  fecha_reparto DATETIME,
  processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (batch_id) REFERENCES lotes_procesamiento(id),
  FOREIGN KEY (uploaded_file_id) REFERENCES archivos_subidos(id)
);

CREATE TABLE consolidado_detalle (
  id INT AUTO_INCREMENT PRIMARY KEY,
  consolidado_id INT NOT NULL,
  sku VARCHAR(128) NOT NULL,
  descripcion VARCHAR(255),
  bultos INT NOT NULL DEFAULT 0,
  unidades INT NOT NULL DEFAULT 0,
  unidades_equivalentes DECIMAL(12,4) NOT NULL DEFAULT 0,
  pallets_completos INT NOT NULL DEFAULT 0,
  bultos_pickear INT NOT NULL DEFAULT 0,
  unidades_sueltas INT NOT NULL DEFAULT 0,
  almacen VARCHAR(120),
  cancha VARCHAR(120),
  prioridad VARCHAR(50),
  sku_estado VARCHAR(80),
  FOREIGN KEY (consolidado_id) REFERENCES consolidados(id)
);

CREATE TABLE logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  action VARCHAR(255) NOT NULL,
  entity VARCHAR(120),
  entity_id INT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  details TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE errores_procesamiento (
  id INT AUTO_INCREMENT PRIMARY KEY,
  uploaded_file_id INT,
  filename VARCHAR(255) NOT NULL,
  error_message TEXT NOT NULL,
  traceback TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (uploaded_file_id) REFERENCES archivos_subidos(id)
);
