# Custom Label Studio with SSO support
FROM heartexlabs/label-studio:latest

# Install label-studio-sso package
RUN pip install label-studio-sso

# Copy custom settings that will be imported
COPY settings_sso.py /label-studio/label_studio/core/settings/settings_sso.py

# Copy startup script
COPY --chmod=755 entrypoint-sso.sh /entrypoint-sso.sh

# Set environment variables
ENV LABEL_STUDIO_SSO_ENABLED=true

# Expose port
EXPOSE 8080

# Use custom entrypoint with original CMD
ENTRYPOINT ["/entrypoint-sso.sh"]
CMD ["label-studio"]
