# Custom Label Studio with SSO support
FROM heartexlabs/label-studio:latest

# Install label-studio-sso package
RUN pip install label-studio-sso

# Copy custom settings that will be imported
COPY settings_sso.py /label-studio/label_studio/core/settings/settings_sso.py

# Copy custom branding & i18n files for SuperInsight white-labeling
COPY i18n-inject.js /label-studio/custom/i18n-inject.js
COPY branding.css /label-studio/custom/branding.css
# NOTE: Add favicon.svg to deploy/label-studio/ and uncomment the line below
# COPY favicon.svg /label-studio/custom/favicon.svg

# Copy startup script
COPY --chmod=755 entrypoint-sso.sh /entrypoint-sso.sh

# Set environment variables
ENV LABEL_STUDIO_SSO_ENABLED=true

# Expose port
EXPOSE 8080

# Use custom entrypoint with original CMD
ENTRYPOINT ["/entrypoint-sso.sh"]
CMD ["label-studio"]
