    async def _perform_comprehensive_detection(
        self,
        data: Any,
        policy: LeakagePreventionPolicy,
        scan_id: str
    ) -> Dict[str, Any]:
        """Perform comprehensive leakage detection using multiple methods."""
        
        results = {
            "pattern_matching": [],
            "statistical_analysis": {},
            "entropy_analysis": {},
            "hash_comparison": [],
            "presidio_detection": []
        }
        
        # Convert data to text for analysis
        text_data = await self._extract_text_from_data(data)
        
        # 1. Pattern-based detection
        pattern_results = await self._detect_patterns(text_data, policy)
        results["pattern_matching"] = pattern_results
        
        # 2. Presidio-based detection
        presidio_results = await self._detect_with_presidio(text_data)
        results["presidio_detection"] = presidio_results
        
        # 3. Entropy analysis
        entropy_results = await self._analyze_entropy(text_data)
        results["entropy_analysis"] = entropy_results
        
        # 4. Statistical analysis
        stats_results = await self._perform_statistical_analysis(text_data)
        results["statistical_analysis"] = stats_results
        
        # 5. Hash comparison (for known sensitive data)
        hash_results = await self._compare_hashes(text_data, policy.tenant_id)
        results["hash_comparison"] = hash_results
        
        return results
    
    async def _extract_text_from_data(self, data: Any) -> List[str]:
        """Extract text content from various data types."""
        text_content = []
        
        if isinstance(data, str):
            text_content.append(data)
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    text_content.append(value)
                elif isinstance(value, (dict, list)):
                    nested_text = await self._extract_text_from_data(value)
                    text_content.extend(nested_text)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    text_content.append(item)
                elif isinstance(item, (dict, list)):
                    nested_text = await self._extract_text_from_data(item)
                    text_content.extend(nested_text)
        
        return text_content
    
    async def _detect_patterns(
        self,
        text_data: List[str],
        policy: LeakagePreventionPolicy
    ) -> List[Dict[str, Any]]:
        """Detect sensitive patterns in text data."""
        
        detected_patterns = []
        
        for text in text_data:
            if not text or len(text.strip()) < 3:
                continue
                
            for pattern_type, patterns in self.sensitive_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        # Check against whitelist
                        if self._is_whitelisted(match.group(), policy.whitelist_patterns):
                            continue
                            
                        # Check against blacklist
                        if self._is_blacklisted(match.group(), policy.blacklist_patterns):
                            detected_patterns.append({
                                "type": pattern_type,
                                "pattern": pattern,
                                "match": match.group(),
                                "start": match.start(),
                                "end": match.end(),
                                "confidence": 0.9,
                                "method": "pattern_matching",
                                "risk_level": "high"
                            })
                        else:
                            detected_patterns.append({
                                "type": pattern_type,
                                "pattern": pattern,
                                "match": match.group(),
                                "start": match.start(),
                                "end": match.end(),
                                "confidence": 0.8,
                                "method": "pattern_matching",
                                "risk_level": "medium"
                            })
        
        return detected_patterns
    
    async def _detect_with_presidio(self, text_data: List[str]) -> List[Dict[str, Any]]:
        """Use Presidio for advanced PII detection."""
        
        presidio_results = []
        
        for text in text_data:
            if not text or len(text.strip()) < 3:
                continue
                
            try:
                entities = self.presidio_engine.detect_pii(
                    text=text,
                    score_threshold=0.6
                )
                
                for entity in entities:
                    presidio_results.append({
                        "type": entity.entity_type.value,
                        "match": entity.text,
                        "start": entity.start,
                        "end": entity.end,
                        "confidence": entity.score,
                        "method": "presidio",
                        "risk_level": "high" if entity.score > 0.8 else "medium",
                        "metadata": entity.recognition_metadata
                    })
                    
            except Exception as e:
                logger.warning(f"Presidio detection failed: {e}")
        
        return presidio_results
    
    async def _analyze_entropy(self, text_data: List[str]) -> Dict[str, Any]:
        """Analyze entropy to detect potentially encrypted/hashed data."""
        
        import math
        from collections import Counter
        
        entropy_results = {
            "high_entropy_strings": [],
            "average_entropy": 0.0,
            "max_entropy": 0.0,
            "suspicious_strings": []
        }
        
        all_entropies = []
        
        for text in text_data:
            if not text or len(text) < self.entropy_thresholds["min_length"]:
                continue
            
            # Calculate Shannon entropy
            counter = Counter(text)
            length = len(text)
            entropy = -sum((count / length) * math.log2(count / length) 
                          for count in counter.values())
            
            all_entropies.append(entropy)
            
            # Check for high entropy (potentially sensitive)
            if entropy > self.entropy_thresholds["high_entropy"]:
                entropy_results["high_entropy_strings"].append({
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "entropy": entropy,
                    "length": len(text),
                    "risk_level": "high"
                })
            elif entropy > self.entropy_thresholds["medium_entropy"]:
                entropy_results["suspicious_strings"].append({
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "entropy": entropy,
                    "length": len(text),
                    "risk_level": "medium"
                })
        
        if all_entropies:
            entropy_results["average_entropy"] = sum(all_entropies) / len(all_entropies)
            entropy_results["max_entropy"] = max(all_entropies)
        
        return entropy_results
    
    async def _perform_statistical_analysis(self, text_data: List[str]) -> Dict[str, Any]:
        """Perform statistical analysis to detect anomalies."""
        
        stats = {
            "total_strings": len(text_data),
            "average_length": 0.0,
            "max_length": 0,
            "min_length": float('inf'),
            "numeric_strings": 0,
            "alphanumeric_strings": 0,
            "special_char_strings": 0,
            "anomalies": []
        }
        
        if not text_data:
            return stats
        
        lengths = []
        
        for text in text_data:
            if not text:
                continue
                
            length = len(text)
            lengths.append(length)
            
            # Count string types
            if text.isdigit():
                stats["numeric_strings"] += 1
            elif text.isalnum():
                stats["alphanumeric_strings"] += 1
            elif re.search(r'[!@#$%^&*(),.?":{}|<>]', text):
                stats["special_char_strings"] += 1
            
            # Detect anomalies
            if length > 1000:  # Very long strings
                stats["anomalies"].append({
                    "type": "long_string",
                    "text": text[:100] + "...",
                    "length": length,
                    "risk_level": "medium"
                })
            
            # Check for repeated patterns (potential tokens/keys)
            if len(set(text)) < len(text) * 0.3 and length > 20:
                stats["anomalies"].append({
                    "type": "low_character_diversity",
                    "text": text[:50] + "...",
                    "diversity_ratio": len(set(text)) / len(text),
                    "risk_level": "medium"
                })
        
        if lengths:
            stats["average_length"] = sum(lengths) / len(lengths)
            stats["max_length"] = max(lengths)
            stats["min_length"] = min(lengths)
        
        return stats
    
    async def _compare_hashes(self, text_data: List[str], tenant_id: str) -> List[Dict[str, Any]]:
        """Compare against known sensitive data hashes."""
        
        hash_matches = []
        
        # Get known sensitive data hashes for tenant
        known_hashes = await self._get_known_sensitive_hashes(tenant_id)
        
        for text in text_data:
            if not text or len(text.strip()) < 3:
                continue
            
            # Generate hashes for comparison
            text_hash_md5 = hashlib.md5(text.encode()).hexdigest()
            text_hash_sha256 = hashlib.sha256(text.encode()).hexdigest()
            
            # Check against known hashes
            if text_hash_md5 in known_hashes or text_hash_sha256 in known_hashes:
                hash_matches.append({
                    "type": "known_sensitive_data",
                    "hash_md5": text_hash_md5,
                    "hash_sha256": text_hash_sha256,
                    "text_preview": text[:20] + "..." if len(text) > 20 else text,
                    "confidence": 1.0,
                    "method": "hash_comparison",
                    "risk_level": "critical"
                })
        
        return hash_matches
    
    async def _get_known_sensitive_hashes(self, tenant_id: str) -> Set[str]:
        """Get known sensitive data hashes for tenant."""
        
        # This would typically query a database of known sensitive data hashes
        # For now, return empty set as placeholder
        return set()
    
    def _is_whitelisted(self, text: str, whitelist_patterns: List[str]) -> bool:
        """Check if text matches whitelist patterns."""
        
        for pattern in whitelist_patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            except re.error:
                # Invalid regex, skip
                continue
        
        return False
    
    def _is_blacklisted(self, text: str, blacklist_patterns: List[str]) -> bool:
        """Check if text matches blacklist patterns."""
        
        for pattern in blacklist_patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            except re.error:
                # Invalid regex, skip
                continue
        
        return False
    
    async def _analyze_detection_results(
        self,
        detection_results: Dict[str, Any],
        policy: LeakagePreventionPolicy,
        scan_id: str
    ) -> LeakageDetectionResult:
        """Analyze all detection results and determine final risk assessment."""
        
        all_detected_entities = []
        all_leakage_patterns = []
        detection_methods = []
        recommendations = []
        
        # Aggregate pattern matching results
        pattern_results = detection_results.get("pattern_matching", [])
        if pattern_results:
            all_detected_entities.extend(pattern_results)
            all_leakage_patterns.extend([r["type"] for r in pattern_results])
            detection_methods.append(LeakageDetectionMethod.PATTERN_MATCHING)
        
        # Aggregate Presidio results
        presidio_results = detection_results.get("presidio_detection", [])
        if presidio_results:
            all_detected_entities.extend(presidio_results)
            all_leakage_patterns.extend([r["type"] for r in presidio_results])
            detection_methods.append(LeakageDetectionMethod.MACHINE_LEARNING)
        
        # Analyze entropy results
        entropy_results = detection_results.get("entropy_analysis", {})
        high_entropy_strings = entropy_results.get("high_entropy_strings", [])
        if high_entropy_strings:
            all_detected_entities.extend(high_entropy_strings)
            all_leakage_patterns.append("high_entropy_data")
            detection_methods.append(LeakageDetectionMethod.ENTROPY_ANALYSIS)
        
        # Analyze statistical anomalies
        stats_results = detection_results.get("statistical_analysis", {})
        anomalies = stats_results.get("anomalies", [])
        if anomalies:
            all_detected_entities.extend(anomalies)
            all_leakage_patterns.extend([a["type"] for a in anomalies])
            detection_methods.append(LeakageDetectionMethod.STATISTICAL_ANALYSIS)
        
        # Check hash comparison results
        hash_results = detection_results.get("hash_comparison", [])
        if hash_results:
            all_detected_entities.extend(hash_results)
            all_leakage_patterns.append("known_sensitive_data")
            detection_methods.append(LeakageDetectionMethod.HASH_COMPARISON)
        
        # Determine overall risk level and confidence
        has_leakage = len(all_detected_entities) > 0
        risk_level = self._calculate_risk_level(all_detected_entities, policy)
        confidence_score = self._calculate_confidence_score(all_detected_entities, detection_methods)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            all_detected_entities, risk_level, policy
        )
        
        return LeakageDetectionResult(
            has_leakage=has_leakage,
            risk_level=risk_level,
            confidence_score=confidence_score,
            detected_entities=all_detected_entities,
            leakage_patterns=list(set(all_leakage_patterns)),
            detection_methods=detection_methods,
            recommendations=recommendations,
            metadata={
                "scan_id": scan_id,
                "total_entities": len(all_detected_entities),
                "detection_summary": {
                    "pattern_matches": len(pattern_results),
                    "presidio_matches": len(presidio_results),
                    "entropy_anomalies": len(high_entropy_strings),
                    "statistical_anomalies": len(anomalies),
                    "hash_matches": len(hash_results)
                }
            }
        )
    
    def _calculate_risk_level(
        self,
        detected_entities: List[Dict[str, Any]],
        policy: LeakagePreventionPolicy
    ) -> LeakageRiskLevel:
        """Calculate overall risk level based on detected entities."""
        
        if not detected_entities:
            return LeakageRiskLevel.NONE
        
        # Count entities by risk level
        critical_count = sum(1 for e in detected_entities if e.get("risk_level") == "critical")
        high_count = sum(1 for e in detected_entities if e.get("risk_level") == "high")
        medium_count = sum(1 for e in detected_entities if e.get("risk_level") == "medium")
        
        # Determine overall risk
        if critical_count > 0:
            return LeakageRiskLevel.CRITICAL
        elif high_count >= 3 or (high_count >= 1 and policy.strict_mode):
            return LeakageRiskLevel.HIGH
        elif high_count >= 1 or medium_count >= 5:
            return LeakageRiskLevel.MEDIUM
        elif medium_count >= 1:
            return LeakageRiskLevel.LOW
        else:
            return LeakageRiskLevel.NONE
    
    def _calculate_confidence_score(
        self,
        detected_entities: List[Dict[str, Any]],
        detection_methods: List[LeakageDetectionMethod]
    ) -> float:
        """Calculate confidence score based on detection results."""
        
        if not detected_entities:
            return 1.0  # High confidence in no leakage
        
        # Base confidence from individual detections
        confidences = [e.get("confidence", 0.5) for e in detected_entities]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Boost confidence if multiple methods agree
        method_boost = min(len(detection_methods) * 0.1, 0.3)
        
        # Boost confidence for high-risk detections
        high_risk_count = sum(1 for e in detected_entities 
                             if e.get("risk_level") in ["high", "critical"])
        risk_boost = min(high_risk_count * 0.05, 0.2)
        
        final_confidence = min(avg_confidence + method_boost + risk_boost, 1.0)
        return final_confidence
    
    def _generate_recommendations(
        self,
        detected_entities: List[Dict[str, Any]],
        risk_level: LeakageRiskLevel,
        policy: LeakagePreventionPolicy
    ) -> List[str]:
        """Generate recommendations based on detection results."""
        
        recommendations = []
        
        if not detected_entities:
            recommendations.append("No sensitive data leakage detected. Continue monitoring.")
            return recommendations
        
        # Risk-based recommendations
        if risk_level == LeakageRiskLevel.CRITICAL:
            recommendations.extend([
                "CRITICAL: Immediate action required to prevent data leakage",
                "Block all data operations until leakage is resolved",
                "Conduct emergency security review",
                "Notify security team and data protection officer"
            ])
        elif risk_level == LeakageRiskLevel.HIGH:
            recommendations.extend([
                "HIGH RISK: Review and enhance data masking rules",
                "Implement additional access controls",
                "Increase monitoring frequency",
                "Consider temporary data access restrictions"
            ])
        elif risk_level == LeakageRiskLevel.MEDIUM:
            recommendations.extend([
                "MEDIUM RISK: Update desensitization policies",
                "Review user permissions and access patterns",
                "Enhance data classification rules"
            ])
        else:
            recommendations.append("LOW RISK: Monitor and review periodically")
        
        # Entity-specific recommendations
        entity_types = set(e.get("type", "unknown") for e in detected_entities)
        
        if "credit_card" in entity_types:
            recommendations.append("Implement PCI DSS compliant data handling for credit card data")
        
        if "ssn" in entity_types:
            recommendations.append("Apply strict access controls for Social Security Numbers")
        
        if "email" in entity_types:
            recommendations.append("Review email data handling and privacy policies")
        
        if "api_key" in entity_types:
            recommendations.append("Rotate API keys and implement secure key management")
        
        if "high_entropy_data" in [e.get("type") for e in detected_entities]:
            recommendations.append("Review encrypted/hashed data handling procedures")
        
        return recommendations
    
    async def prevent_data_export(
        self,
        export_data: Any,
        tenant_id: str,
        user_id: str,
        export_format: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Prevent sensitive data export by scanning before export.
        
        Args:
            export_data: Data to be exported
            tenant_id: Tenant identifier
            user_id: User identifier
            export_format: Format of export (csv, json, etc.)
            
        Returns:
            Dict with prevention result and safe export data
        """
        
        try:
            # Scan export data for leakage
            scan_result = await self.scan_for_leakage(
                data=export_data,
                tenant_id=tenant_id,
                user_id=user_id,
                context={"operation": "data_export", "format": export_format},
                operation_type="export_prevention"
            )
            
            # If leakage detected, apply prevention measures
            if scan_result.has_leakage:
                if scan_result.risk_level in [LeakageRiskLevel.CRITICAL, LeakageRiskLevel.HIGH]:
                    # Block export entirely
                    return {
                        "allowed": False,
                        "blocked": True,
                        "reason": f"Export blocked due to {scan_result.risk_level.value} risk data leakage",
                        "risk_level": scan_result.risk_level.value,
                        "detected_entities": len(scan_result.detected_entities),
                        "recommendations": scan_result.recommendations,
                        "safe_export_data": None
                    }
                else:
                    # Apply automatic masking and allow export
                    safe_data = await self._create_safe_export_data(
                        export_data, scan_result, tenant_id
                    )
                    
                    return {
                        "allowed": True,
                        "blocked": False,
                        "masked": True,
                        "reason": f"Export allowed with automatic masking due to {scan_result.risk_level.value} risk",
                        "risk_level": scan_result.risk_level.value,
                        "detected_entities": len(scan_result.detected_entities),
                        "recommendations": scan_result.recommendations,
                        "safe_export_data": safe_data
                    }
            else:
                # No leakage detected, allow export
                return {
                    "allowed": True,
                    "blocked": False,
                    "masked": False,
                    "reason": "No sensitive data leakage detected",
                    "risk_level": "none",
                    "detected_entities": 0,
                    "recommendations": [],
                    "safe_export_data": export_data
                }
                
        except Exception as e:
            logger.error(f"Export prevention failed: {e}")
            
            # Fail safe - block export on error
            return {
                "allowed": False,
                "blocked": True,
                "reason": f"Export blocked due to prevention system error: {str(e)}",
                "risk_level": "unknown",
                "detected_entities": 0,
                "recommendations": ["Manual review required due to system error"],
                "safe_export_data": None
            }
    
    async def _create_safe_export_data(
        self,
        original_data: Any,
        scan_result: LeakageDetectionResult,
        tenant_id: str
    ) -> Any:
        """Create safe export data by applying automatic masking."""
        
        try:
            # Get active desensitization rules
            async with get_db_session() as db:
                rules = self.rule_manager.get_rules_for_tenant(
                    tenant_id=tenant_id,
                    enabled_only=True,
                    db=db
                )
            
            if isinstance(original_data, str):
                # Apply masking to text
                result = self.presidio_engine.anonymize_text(
                    text=original_data,
                    rules=rules
                )
                return result.anonymized_text
                
            elif isinstance(original_data, dict):
                # Apply masking to dictionary values
                safe_dict = {}
                for key, value in original_data.items():
                    if isinstance(value, str):
                        result = self.presidio_engine.anonymize_text(
                            text=value,
                            rules=rules
                        )
                        safe_dict[key] = result.anonymized_text
                    else:
                        safe_dict[key] = value
                return safe_dict
                
            elif isinstance(original_data, list):
                # Apply masking to list items
                safe_list = []
                for item in original_data:
                    if isinstance(item, str):
                        result = self.presidio_engine.anonymize_text(
                            text=item,
                            rules=rules
                        )
                        safe_list.append(result.anonymized_text)
                    elif isinstance(item, dict):
                        safe_item = await self._create_safe_export_data(item, scan_result, tenant_id)
                        safe_list.append(safe_item)
                    else:
                        safe_list.append(item)
                return safe_list
            
            else:
                # Return as-is for other data types
                return original_data
                
        except Exception as e:
            logger.error(f"Failed to create safe export data: {e}")
            # Return None to indicate masking failed
            return None
    
    async def get_leakage_statistics(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get leakage detection statistics for a tenant."""
        
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            # Query leakage scan events
            scan_events = await self.audit_service.query_audit_events(
                event_type="leakage_scan_complete",
                tenant_id=tenant_id,
                start_time=start_date,
                end_time=end_date
            )
            
            # Analyze statistics
            total_scans = len(scan_events)
            leakage_detected = sum(1 for e in scan_events 
                                 if e.get("details", {}).get("has_leakage", False))
            
            risk_levels = {}
            for event in scan_events:
                risk_level = event.get("details", {}).get("risk_level", "none")
                risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_scans": total_scans,
                "leakage_detected": leakage_detected,
                "leakage_rate": leakage_detected / total_scans if total_scans > 0 else 0.0,
                "risk_level_distribution": risk_levels,
                "zero_leakage_compliance": (total_scans - leakage_detected) / total_scans if total_scans > 0 else 1.0
            }
            
        except Exception as e:
            logger.error(f"Failed to get leakage statistics for tenant {tenant_id}: {e}")
            return {"error": str(e)}