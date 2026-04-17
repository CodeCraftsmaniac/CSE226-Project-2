class HealthModel {
  const HealthModel({
    required this.overallStatus,
    required this.uptimeSeconds,
    required this.backend,
    required this.database,
    required this.ocr,
    required this.metrics,
  });

  final String overallStatus;
  final int uptimeSeconds;
  final LayerHealth backend;
  final LayerHealth database;
  final LayerHealth ocr;
  final HealthMetrics metrics;

  bool get isHealthy {
    final normalized = overallStatus.toLowerCase();
    return normalized == 'healthy' ||
        normalized == 'ok' ||
        normalized == 'up' ||
        normalized == 'operational' ||
        (backend.isUp && database.isUp && ocr.isUp);
  }

  factory HealthModel.fromJson(Map<String, dynamic> json) {
    final layers = _asMap(json['layers']);

    final backendJson = _layerPayload(
      layers: layers,
      root: json,
      primaryKey: 'backend',
      alternateKeys: const ['api'],
    );
    final databaseJson = _layerPayload(
      layers: layers,
      root: json,
      primaryKey: 'database',
      alternateKeys: const ['db'],
    );
    final ocrJson = _layerPayload(
      layers: layers,
      root: json,
      primaryKey: 'ocr',
      alternateKeys: const ['ocr_engine', 'engine'],
    );

    final uptime = _extractUptimeSeconds(json);
    final metricsJson = _asMap(json['metrics']);

    return HealthModel(
      overallStatus: _pickString(
        json,
        const ['status', 'overall_status', 'overallStatus'],
        fallback: 'unknown',
      ),
      uptimeSeconds: uptime,
      backend: LayerHealth.fromJson(backendJson),
      database: LayerHealth.fromJson(databaseJson),
      ocr: LayerHealth.fromJson(ocrJson),
      metrics: HealthMetrics.fromJson(metricsJson),
    );
  }

  factory HealthModel.error() {
    const down = LayerHealth(status: 'unreachable', latencyMs: 999);
    return HealthModel(
      overallStatus: 'unreachable',
      uptimeSeconds: 0,
      backend: down,
      database: down,
      ocr: down,
      metrics: HealthMetrics.empty(),
    );
  }

  static Map<String, dynamic> _layerPayload({
    required Map<String, dynamic> layers,
    required Map<String, dynamic> root,
    required String primaryKey,
    required List<String> alternateKeys,
  }) {
    if (layers.isNotEmpty) {
      final fromLayers = _firstMap(layers, [primaryKey, ...alternateKeys]);
      if (fromLayers.isNotEmpty) {
        return fromLayers;
      }
    }

    final fromRoot = _firstMap(root, [primaryKey, ...alternateKeys]);
    if (fromRoot.isNotEmpty) {
      return fromRoot;
    }

    return const <String, dynamic>{};
  }

  static int _extractUptimeSeconds(Map<String, dynamic> json) {
    final uptimeObj = _asMap(json['uptime']);
    if (uptimeObj.isNotEmpty) {
      return _asInt(
        uptimeObj['seconds'] ??
            uptimeObj['uptime_seconds'] ??
            uptimeObj['value'],
      );
    }

    return _asInt(json['uptime_seconds'] ?? json['uptimeSeconds']);
  }

  static String _pickString(
    Map<String, dynamic> source,
    List<String> keys, {
    String fallback = '',
  }) {
    for (final key in keys) {
      final value = source[key];
      if (value is String && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return fallback;
  }

  static Map<String, dynamic> _firstMap(
    Map<String, dynamic> source,
    List<String> keys,
  ) {
    for (final key in keys) {
      final map = _asMap(source[key]);
      if (map.isNotEmpty) {
        return map;
      }
    }
    return const <String, dynamic>{};
  }

  static Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return value.cast<String, dynamic>();
    }
    return const <String, dynamic>{};
  }

  static int _asInt(dynamic value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.round();
    }
    if (value is String) {
      return int.tryParse(value) ?? double.tryParse(value)?.round() ?? 0;
    }
    return 0;
  }
}

class LayerHealth {
  const LayerHealth({
    required this.status,
    required this.latencyMs,
    this.message,
    this.memoryMb,
    this.provider,
  });

  final String status;
  final int latencyMs;
  final String? message;
  final int? memoryMb;
  final String? provider;

  bool get isUp {
    switch (status.toLowerCase()) {
      case 'up':
      case 'healthy':
      case 'ok':
      case 'operational':
      case 'connected':
      case 'active':
      case 'ready':
        return true;
      default:
        return false;
    }
  }

  factory LayerHealth.fromJson(Map<String, dynamic> json) {
    return LayerHealth(
      status: _pickString(
        json,
        const ['status', 'state', 'health'],
        fallback: 'unknown',
      ),
      latencyMs: _asInt(
        json['latency_ms'] ??
            json['latency'] ??
            json['response_time_ms'] ??
            json['response_time'],
      ),
      message: _pickString(
        json,
        const ['message', 'note', 'detail', 'details'],
      ),
      memoryMb: json['memory_mb'] != null ? _asInt(json['memory_mb']) : null,
      provider: _pickString(
        json,
        const ['provider'],
      ).isEmpty
          ? null
          : _pickString(json, const ['provider']),
    );
  }

  static String _pickString(
    Map<String, dynamic> source,
    List<String> keys, {
    String fallback = '',
  }) {
    for (final key in keys) {
      final value = source[key];
      if (value is String && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return fallback;
  }

  static int _asInt(dynamic value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.round();
    }
    if (value is String) {
      return int.tryParse(value) ?? double.tryParse(value)?.round() ?? 0;
    }
    return 0;
  }
}

class HealthMetrics {
  const HealthMetrics({
    required this.userRequests,
    required this.healthChecks,
    required this.errors,
    required this.errorRate,
  });

  final int userRequests;
  final int healthChecks;
  final int errors;
  final double errorRate;

  factory HealthMetrics.fromJson(Map<String, dynamic> json) {
    return HealthMetrics(
      userRequests: _asInt(json['user_requests'] ?? json['userRequests'] ?? 0),
      healthChecks: _asInt(json['health_checks'] ?? json['healthChecks'] ?? 0),
      errors: _asInt(json['errors'] ?? 0),
      errorRate: _asDouble(json['error_rate'] ?? json['errorRate'] ?? 0.0),
    );
  }

  factory HealthMetrics.empty() {
    return const HealthMetrics(
      userRequests: 0,
      healthChecks: 0,
      errors: 0,
      errorRate: 0.0,
    );
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.round();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static double _asDouble(dynamic value) {
    if (value is double) return value;
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }
}
