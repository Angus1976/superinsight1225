// Neo4j Schema for Ontology Expert Collaboration
// Run this script to set up the graph database schema
// Usage: cat scripts/neo4j_ontology_schema.cypher | cypher-shell -u neo4j -p <password>

// ============================================
// Node Constraints and Indexes
// ============================================

// EntityType nodes - represent ontology entity types
CREATE CONSTRAINT entity_type_id IF NOT EXISTS
FOR (e:EntityType) REQUIRE e.id IS UNIQUE;

CREATE INDEX entity_type_tenant IF NOT EXISTS
FOR (e:EntityType) ON (e.tenant_id);

CREATE INDEX entity_type_ontology IF NOT EXISTS
FOR (e:EntityType) ON (e.ontology_id);

CREATE INDEX entity_type_name IF NOT EXISTS
FOR (e:EntityType) ON (e.name);

// RelationType nodes - represent ontology relation types
CREATE CONSTRAINT relation_type_id IF NOT EXISTS
FOR (r:RelationType) REQUIRE r.id IS UNIQUE;

CREATE INDEX relation_type_tenant IF NOT EXISTS
FOR (r:RelationType) ON (r.tenant_id);

CREATE INDEX relation_type_ontology IF NOT EXISTS
FOR (r:RelationType) ON (r.ontology_id);

// Expert nodes - represent domain experts
CREATE CONSTRAINT expert_id IF NOT EXISTS
FOR (e:Expert) REQUIRE e.id IS UNIQUE;

CREATE INDEX expert_tenant IF NOT EXISTS
FOR (e:Expert) ON (e.tenant_id);

CREATE INDEX expert_email IF NOT EXISTS
FOR (e:Expert) ON (e.email);

// Template nodes - represent ontology templates
CREATE CONSTRAINT template_id IF NOT EXISTS
FOR (t:Template) REQUIRE t.id IS UNIQUE;

CREATE INDEX template_tenant IF NOT EXISTS
FOR (t:Template) ON (t.tenant_id);

CREATE INDEX template_industry IF NOT EXISTS
FOR (t:Template) ON (t.industry);

// Project nodes - represent ontology projects
CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE INDEX project_tenant IF NOT EXISTS
FOR (p:Project) ON (p.tenant_id);

// Ontology nodes - represent ontology instances
CREATE CONSTRAINT ontology_id IF NOT EXISTS
FOR (o:Ontology) REQUIRE o.id IS UNIQUE;

CREATE INDEX ontology_tenant IF NOT EXISTS
FOR (o:Ontology) ON (o.tenant_id);

// ChangeRequest nodes - represent change requests
CREATE CONSTRAINT change_request_id IF NOT EXISTS
FOR (c:ChangeRequest) REQUIRE c.id IS UNIQUE;

CREATE INDEX change_request_status IF NOT EXISTS
FOR (c:ChangeRequest) ON (c.status);

// ============================================
// Relationship Types
// ============================================

// CONTRIBUTED_TO - Expert contributed to an ontology element
// (Expert)-[:CONTRIBUTED_TO {contribution_type, quality_score, created_at}]->(EntityType|RelationType)

// DERIVED_FROM - Template or ontology derived from another
// (Template)-[:DERIVED_FROM {version, customizations}]->(Template)
// (Ontology)-[:DERIVED_FROM {instantiated_at}]->(Template)

// USED_BY - Entity type used by projects or other entities
// (EntityType)-[:USED_BY {usage_count, last_used_at}]->(Project)
// (EntityType)-[:USED_BY]->(EntityType)

// DEPENDS_ON - Dependency relationship for impact analysis
// (EntityType)-[:DEPENDS_ON {dependency_type}]->(EntityType)
// (RelationType)-[:DEPENDS_ON]->(EntityType)

// CONNECTS - Relation type connects entity types
// (RelationType)-[:CONNECTS {role: 'source'|'target'}]->(EntityType)

// BELONGS_TO - Element belongs to ontology
// (EntityType)-[:BELONGS_TO]->(Ontology)
// (RelationType)-[:BELONGS_TO]->(Ontology)

// REQUESTED_BY - Change request created by expert
// (ChangeRequest)-[:REQUESTED_BY]->(Expert)

// AFFECTS - Change request affects elements
// (ChangeRequest)-[:AFFECTS {change_type}]->(EntityType|RelationType)

// APPROVED_BY - Change request approved by expert
// (ChangeRequest)-[:APPROVED_BY {level, approved_at}]->(Expert)

// HAS_EXPERTISE - Expert has expertise in area
// (Expert)-[:HAS_EXPERTISE {level, certified}]->(ExpertiseArea)

// ============================================
// Sample Data Creation (for testing)
// ============================================

// Create expertise area nodes
MERGE (ea1:ExpertiseArea {name: 'entity_modeling', display_name_zh: '实体建模', display_name_en: 'Entity Modeling'})
MERGE (ea2:ExpertiseArea {name: 'relation_design', display_name_zh: '关系设计', display_name_en: 'Relation Design'})
MERGE (ea3:ExpertiseArea {name: 'attribute_definition', display_name_zh: '属性定义', display_name_en: 'Attribute Definition'})
MERGE (ea4:ExpertiseArea {name: 'validation_rules', display_name_zh: '验证规则', display_name_en: 'Validation Rules'})
MERGE (ea5:ExpertiseArea {name: 'compliance', display_name_zh: '合规性', display_name_en: 'Compliance'})
MERGE (ea6:ExpertiseArea {name: 'industry_finance', display_name_zh: '金融行业', display_name_en: 'Finance Industry'})
MERGE (ea7:ExpertiseArea {name: 'industry_healthcare', display_name_zh: '医疗行业', display_name_en: 'Healthcare Industry'})
MERGE (ea8:ExpertiseArea {name: 'industry_manufacturing', display_name_zh: '制造行业', display_name_en: 'Manufacturing Industry'})

// ============================================
// Utility Queries
// ============================================

// Query: Find all dependencies of an entity type (for impact analysis)
// MATCH path = (e:EntityType {id: $entity_id})<-[:DEPENDS_ON*1..5]-(dependent)
// RETURN dependent, length(path) as distance

// Query: Find experts with expertise in a specific area
// MATCH (e:Expert)-[r:HAS_EXPERTISE]->(ea:ExpertiseArea {name: $area})
// WHERE r.level >= 3
// RETURN e ORDER BY r.level DESC

// Query: Get template lineage
// MATCH path = (t:Template {id: $template_id})-[:DERIVED_FROM*]->(parent:Template)
// RETURN path

// Query: Find all elements affected by a change request
// MATCH (cr:ChangeRequest {id: $change_request_id})-[:AFFECTS]->(element)
// RETURN element

// Query: Get contribution history for an expert
// MATCH (e:Expert {id: $expert_id})-[c:CONTRIBUTED_TO]->(element)
// RETURN element, c.contribution_type, c.quality_score, c.created_at
// ORDER BY c.created_at DESC
