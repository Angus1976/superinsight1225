/**
 * Label Studio Annotation Templates
 * 
 * XML templates for different annotation types
 */

import type { AnnotationType } from '@/types/task';

/**
 * Text Classification Template
 * Supports single and multi-label classification
 */
export const TEXT_CLASSIFICATION_TEMPLATE = `
<View>
  <Text name="text" value="$text"/>
  <Choices name="label" toName="text" choice="single-radio">
    <Choice value="Positive"/>
    <Choice value="Negative"/>
    <Choice value="Neutral"/>
  </Choices>
</View>
`.trim();

/**
 * Named Entity Recognition (NER) Template
 */
export const NER_TEMPLATE = `
<View>
  <Labels name="label" toName="text">
    <Label value="Person" background="red"/>
    <Label value="Organization" background="blue"/>
    <Label value="Location" background="green"/>
    <Label value="Date" background="orange"/>
    <Label value="Product" background="purple"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
`.trim();

/**
 * Sentiment Analysis Template
 */
export const SENTIMENT_TEMPLATE = `
<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single-radio">
    <Choice value="Very Positive"/>
    <Choice value="Positive"/>
    <Choice value="Neutral"/>
    <Choice value="Negative"/>
    <Choice value="Very Negative"/>
  </Choices>
</View>
`.trim();

/**
 * Question & Answer Template
 */
export const QA_TEMPLATE = `
<View>
  <Text name="text" value="$text"/>
  <Header value="Question"/>
  <TextArea name="question" toName="text" placeholder="Enter question..." rows="2"/>
  <Header value="Answer"/>
  <TextArea name="answer" toName="text" placeholder="Enter answer..." rows="4"/>
</View>
`.trim();

/**
 * Custom Template (basic text with free-form labels)
 */
export const CUSTOM_TEMPLATE = `
<View>
  <Text name="text" value="$text"/>
  <TextArea name="annotation" toName="text" placeholder="Enter annotation..." rows="4"/>
</View>
`.trim();

/**
 * Get annotation template by type
 */
export const getAnnotationTemplate = (annotationType: AnnotationType): string => {
  switch (annotationType) {
    case 'text_classification':
      return TEXT_CLASSIFICATION_TEMPLATE;
    case 'ner':
      return NER_TEMPLATE;
    case 'sentiment':
      return SENTIMENT_TEMPLATE;
    case 'qa':
      return QA_TEMPLATE;
    case 'custom':
    default:
      return CUSTOM_TEMPLATE;
  }
};

/**
 * Generate custom classification template with provided categories
 */
export const generateClassificationTemplate = (
  categories: string[],
  multiLabel: boolean = false
): string => {
  const choiceType = multiLabel ? 'multiple' : 'single-radio';
  const choices = categories.map(cat => `    <Choice value="${cat}"/>`).join('\n');
  
  return `
<View>
  <Text name="text" value="$text"/>
  <Choices name="label" toName="text" choice="${choiceType}">
${choices}
  </Choices>
</View>
`.trim();
};

/**
 * Generate custom NER template with provided entity types
 */
export const generateNERTemplate = (entityTypes: string[]): string => {
  const colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'gold'];
  const labels = entityTypes.map((entity, index) => 
    `    <Label value="${entity}" background="${colors[index % colors.length]}"/>`
  ).join('\n');
  
  return `
<View>
  <Labels name="label" toName="text">
${labels}
  </Labels>
  <Text name="text" value="$text"/>
</View>
`.trim();
};

/**
 * Generate sentiment template with custom scale
 */
export const generateSentimentTemplate = (
  scale: 'binary' | 'ternary' | 'five_point'
): string => {
  let choices: string[];
  
  switch (scale) {
    case 'binary':
      choices = ['Positive', 'Negative'];
      break;
    case 'ternary':
      choices = ['Positive', 'Neutral', 'Negative'];
      break;
    case 'five_point':
    default:
      choices = ['Very Positive', 'Positive', 'Neutral', 'Negative', 'Very Negative'];
  }
  
  const choiceElements = choices.map(c => `    <Choice value="${c}"/>`).join('\n');
  
  return `
<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single-radio">
${choiceElements}
  </Choices>
</View>
`.trim();
};

export default {
  getAnnotationTemplate,
  generateClassificationTemplate,
  generateNERTemplate,
  generateSentimentTemplate,
};
