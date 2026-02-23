# AWS Deployment Guide

This guide provides step-by-step instructions for deploying the AI Employee system on Amazon Web Services (AWS).

## Architecture Overview

```
                    ┌─────────────────┐
                    │   Route 53      │
                    │   (DNS)         │
                    └─────────┬───────┘
                              │
                    ┌─────────▼───────┐
                    │  CloudFront     │
                    │   (CDN)         │
                    └─────────┬───────┘
                              │
                    ┌─────────▼───────┐
                    │  Application    │
                    │  Load Balancer  │
                    └─────────┬───────┘
                              │
               ┌──────────────┴──────────────┐
               │                              │
    ┌──────────▼───────────┐    ┌───────────▼───────────┐
    │   ECS Fargate        │    │   ECS Fargate        │
    │   (App Containers)   │    │   (App Containers)   │
    └──────────┬───────────┘    └───────────┬───────────┘
               │                              │
               └──────────────┬──────────────┘
                              │
                    ┌─────────▼───────┐
                    │   RDS            │
                    │  (PostgreSQL)    │
                    └──────────────────┘
```

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI installed and configured
- Docker installed locally
- Domain name (optional)

## 1. VPC Setup

### Create VPC
```bash
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ai-employee-vpc}]'

# Get VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters Name=tag:Name,Values=ai-employee-vpc --query 'Vpcs[0].VpcId' --output text)
```

### Create Subnets
```bash
# Create public subnets
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ai-employee-public-1a}]'

aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ai-employee-public-1b}]'

# Create private subnets
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.11.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ai-employee-private-1a}]'

aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.12.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ai-employee-private-1b}]'
```

### Create Internet Gateway
```bash
aws ec2 create-internet-gateway \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=ai-employee-igw}]'

IGW_ID=$(aws ec2 describe-internet-gateways --filters Name=tag:Name,Values=ai-employee-igw --query 'InternetGateways[0].InternetGatewayId' --output text)

aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
```

### Create Route Tables
```bash
# Public route table
aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=ai-employee-public-rt}]'

PUBLIC_RT_ID=$(aws ec2 describe-route-tables --filters Name=tag:Name,Values=ai-employee-public-rt --query 'RouteTables[0].RouteTableId' --output text)

# Add route to internet gateway
aws ec2 create-route \
    --route-table-id $PUBLIC_RT_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID

# Associate public subnets
PUBLIC_SUBNET_1A=$(aws ec2 describe-subnets --filters Name=tag:Name,Values=ai-employee-public-1a --query 'Subnets[0].SubnetId' --output text)
PUBLIC_SUBNET_1B=$(aws ec2 describe-subnets --filters Name=tag:Name,Values=ai-employee-public-1b --query 'Subnets[0].SubnetId' --output text)

aws ec2 associate-route-table --route-table-id $PUBLIC_RT_ID --subnet-id $PUBLIC_SUBNET_1A
aws ec2 associate-route-table --route-table-id $PUBLIC_RT_ID --subnet-id $PUBLIC_SUBNET_1B
```

## 2. Security Groups

### Application Security Group
```bash
aws ec2 create-security-group \
    --group-name ai-employee-sg \
    --description "Security group for AI Employee" \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=ai-employee-sg}]'

SG_ID=$(aws ec2 describe-security-groups --group-names ai-employee-sg --query 'SecurityGroups[0].GroupId' --output text)

# Allow HTTP from load balancer
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG_ID

# Allow all internal traffic
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol -1 \
    --source-group $SG_ID
```

### Database Security Group
```bash
aws ec2 create-security-group \
    --group-name ai-employee-db-sg \
    --description "Security group for RDS database" \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=ai-employee-db-sg}]'

DB_SG_ID=$(aws ec2 describe-security-groups --group-names ai-employee-db-sg --query 'SecurityGroups[0].GroupId' --output text)

# Allow database access from application
aws ec2 authorize-security-group-ingress \
    --group-id $DB_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $SG_ID
```

## 3. RDS Database

### Create Subnet Group
```bash
PRIVATE_SUBNET_1A=$(aws ec2 describe-subnets --filters Name=tag:Name,Values=ai-employee-private-1a --query 'Subnets[0].SubnetId' --output text)
PRIVATE_SUBNET_1B=$(aws ec2 describe-subnets --filters Name=tag:Name,Values=ai-employee-private-1b --query 'Subnets[0].SubnetId' --output text)

aws rds create-db-subnet-group \
    --db-subnet-group-name ai-employee-subnet-group \
    --db-subnet-group-description "Subnet group for AI Employee" \
    --subnet-ids $PRIVATE_SUBNET_1A $PRIVATE_SUBNET_1B
```

### Create Database
```bash
aws rds create-db-instance \
    --db-instance-identifier ai-employee-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username aiemployee \
    --master-user-password YourSecurePassword123! \
    --allocated-storage 20 \
    --storage-type gp2 \
    --vpc-security-group-ids $DB_SG_ID \
    --db-subnet-group-name ai-employee-subnet-group \
    --backup-retention-period 7 \
    --multi-az \
    --storage-encrypted \
    --tag-specifications 'ResourceType=db-instance,Tags=[{Key=Name,Value=ai-employee-db}]'

# Wait for database to be available
aws rds wait db-instance-available --db-instance-identifier ai-employee-db
```

### Get Database Endpoint
```bash
DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier ai-employee-db --query 'DBInstances[0].Endpoint.Address' --output text)
echo "Database endpoint: $DB_ENDPOINT"
```

## 4. ECS Cluster Setup

### Create ECS Cluster
```bash
aws ecs create-cluster \
    --cluster-name ai-employee \
    --service-connect defaults \
    --tag-specifications 'ResourceType=cluster,Tags=[{Key=Name,Value=ai-employee}]'
```

### Create Task Execution Role
```bash
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document file://ecs-trust-policy.json

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### ecs-trust-policy.json
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## 5. ECR Repository

### Create Repository
```bash
aws ecr create-repository \
    --repository-name ai-employee \
    --image-scanning-configuration scanOnPush=true \
    --tag-specifications 'resourceType=repository,tags=[{Key=Name,Value=ai-employee}]'

# Get repository URI
REPO_URI=$(aws ecr describe-repositories --repository-names ai-employee --query 'repositories[0].repositoryUri' --output text)
echo "Repository URI: $REPO_URI"
```

### Push Docker Image
```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $REPO_URI

# Build image
docker build -t ai-employee:latest .

# Tag image
docker tag ai-employee:latest $REPO_URI:latest

# Push image
docker push $REPO_URI:latest
```

## 6. Application Load Balancer

### Create Load Balancer
```bash
aws elbv2 create-load-balancer \
    --name ai-employee-alb \
    --subnets $PUBLIC_SUBNET_1A $PUBLIC_SUBNET_1B \
    --security-groups $ALB_SG_ID \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --tag-specifications 'ResourceType=loadbalancer,Tags=[{Key=Name,Value=ai-employee-alb}]'

ALB_ARN=$(aws elbv2 describe-load-balancers --names ai-employee-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text)
```

### Create Target Group
```bash
aws elbv2 create-target-group \
    --name ai-employee-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /api/v1/health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --matcher HttpCode=200

TG_ARN=$(aws elbv2 describe-target-groups --names ai-employee-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
```

### Create Listener
```bash
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

## 7. ECS Task Definition

### task-definition.json
```json
{
  "family": "ai-employee",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "ai-employee",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/ai-employee:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:ai-employee/db-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:ai-employee/secret-key"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:ai-employee/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-employee",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Register Task Definition
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

## 8. ECS Service

### Create Service
```bash
aws ecs create-service \
    --cluster ai-employee \
    --service-name ai-employee-service \
    --task-definition ai-employee \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1A,$PRIVATE_SUBNET_1B],securityGroups=[$SG_ID],assignPublicIp=DISABLED}" \
    --load-balancers targetGroupArn=$TG_ARN,containerName=ai-employee,containerPort=8000 \
    --health-check-grace-period-seconds 60 \
    --deployment-configuration maximumPercent=200,minimumHealthyPercent=50 \
    --tag-specifications 'ResourceType=service,Tags=[{Key=Name,Value=ai-employee-service}]'
```

## 9. Secrets Manager

### Store Secrets
```bash
# Database URL
aws secretsmanager create-secret \
    --name ai-employee/db-url \
    --description "Database connection string" \
    --secret-string "postgresql://aiemployee:YourSecurePassword123!@$DB_ENDPOINT:5432/aiemployee"

# Secret key
aws secretsmanager create-secret \
    --name ai-employee/secret-key \
    --description "Application secret key" \
    --secret-string "your-super-secret-key-here-min-32-chars"

# JWT secret
aws secretsmanager create-secret \
    --name ai-employee/jwt-secret \
    --description "JWT secret key" \
    --secret-string "your-jwt-secret-key-here-min-32-chars"
```

## 10. CloudWatch Logs

### Create Log Group
```bash
aws logs create-log-group \
    --log-group-name /ecs/ai-employee \
    --retention-in-days 30
```

## 11. Auto Scaling

### Create Auto Scaling Target
```bash
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/ai-employee/ai-employee-service \
    --min-capacity 2 \
    --max-capacity 10 \
    --target-tracking-scaling-policy-configuration file://target-tracking.json
```

### target-tracking.json
```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
```

## 12. Route 53 (Optional)

### Create Hosted Zone
```bash
aws route53 create-hosted-zone \
    --name yourdomain.com \
    --caller-reference $(date +%s)
```

### Create Record Set
```bash
aws route53 change-resource-record-sets \
    --hosted-zone-id YOUR_HOSTED_ZONE_ID \
    --change-batch file://route53-record.json
```

### route53-record.json
```json
{
  "Comment": "Create record set for AI Employee",
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "yourdomain.com",
        "Type": "A",
        "AliasTarget": {
          "DNSName": "ai-employee-alb-123456.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true,
          "HostedZoneId": "Z35SXDOTRQ7X7K"
        }
      }
    }
  ]
}
```

## 13. CloudFront (Optional)

### Create Distribution
```bash
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

### cloudfront-config.json
```json
{
  "CallerReference": "ai-employee-cf-$(date +%s)",
  "Comment": "CloudFront distribution for AI Employee",
  "DefaultRootObject": "",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "origin1",
        "DomainName": "yourdomain.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only"
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "origin1",
    "ViewerProtocolPolicy": "redirect-to-https",
    "TrustedSigners": {
      "Enabled": false,
      "Quantity": 0
    },
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {
        "Forward": "all"
      }
    },
    "MinTTL": 0
  },
  "Enabled": true,
  "PriceClass": "PriceClass_100"
}
```

## Monitoring and Alerting

### CloudWatch Alarms
```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
    --alarm-name ai-employee-high-cpu \
    --alarm-description "High CPU utilization" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:ai-employee-alerts

# High memory alarm
aws cloudwatch put-metric-alarm \
    --alarm-name ai-employee-high-memory \
    --alarm-description "High memory utilization" \
    --metric-name MemoryUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:ai-employee-alerts
```

### SNS Topic for Alerts
```bash
aws sns create-topic \
    --name ai-employee-alerts

# Subscribe email
aws sns subscribe \
    --topic-arn arn:aws:sns:us-east-1:ACCOUNT:ai-employee-alerts \
    --protocol email \
    --notification-endpoint admin@yourdomain.com
```

## Deployment Script

### deploy.sh
```bash
#!/bin/bash

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="ai-employee"
ECS_CLUSTER="ai-employee"
ECS_SERVICE="ai-employee-service"
TASK_FAMILY="ai-employee"

# Get AWS account ID
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# Build and push Docker image
echo "Building Docker image..."
docker build -t $ECR_REPOSITORY:latest .

echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Tagging image..."
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

echo "Pushing image..."
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Update task definition
echo "Updating task definition..."
TASK_DEF=$(aws ecs describe-task-definition --task-definition $TASK_FAMILY --query 'taskDefinition' | jq '.taskDefinitionArn = null')
NEW_TASK_DEF=$(echo $TASK_DEF | jq --arg IMAGE "$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest" '.containerDefinitions[0].image = $IMAGE')

aws ecs register-task-definition --cli-input-json "$NEW_TASK_DEF"

# Update service
echo "Updating ECS service..."
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --force-new-deployment

# Wait for deployment to complete
echo "Waiting for deployment to complete..."
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE

echo "Deployment completed successfully!"
```

## Cost Optimization

### Use Reserved Instances
```bash
aws rds purchase-reserved-db-instances-offering \
    --reserved-db-instances-offering-id offering-id \
    --db-instance-identifier ai-employee-db
```

### Use Savings Plans
```bash
aws ce create-savings-plan \
    --savings-plan-offering-id offering-id \
    --commitment "USD" "10.0" "monthly" \
    --upfront-payment "partial" "10.0"
```

## Security Best Practices

### Enable VPC Flow Logs
```bash
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids $VPC_ID \
    --traffic-type ALL \
    --log-destination-type cloud-watch-logs \
    --log-group-name VPCFlowLogs
```

### Enable AWS Config
```bash
aws configservice put-configuration-recorder \
    --configuration-recorder name=default,roleARN=arn:aws:iam::ACCOUNT:role/aws-config-role

aws configservice start-configuration-recorder \
    --configuration-recorder-name default
```

### Enable CloudTrail
```bash
aws cloudtrail create-trail \
    --name ai-employee-trail \
    --s3-bucket-name my-cloudtrail-bucket \
    --s3-key-prefix cloudtrail-logs \
    --include-global-service-events \
    --is-multi-region-trail
```

## Backup and Disaster Recovery

### Enable Cross-Region RDS Backup
```bash
aws rds modify-db-instance \
    --db-instance-identifier ai-employee-db \
    --backup-retention-period 7 \
    --copy-automated-backups-to-region us-west-2 \
    --apply-immediately
```

### Create S3 Backup Bucket
```bash
aws s3api create-bucket \
    --bucket ai-employee-backups-$(date +%Y) \
    --region us-east-1 \
    --create-bucket-configuration LocationConstraint=us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket ai-employee-backups-$(date +%Y) \
    --versioning-configuration Status=Enabled

# Enable lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket ai-employee-backups-$(date +%Y) \
    --lifecycle-configuration file://backup-lifecycle.json
```

### backup-lifecycle.json
```json
{
  "Rules": [
    {
      "ID": "BackupRule",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### Service Not Starting
```bash
# Check service events
aws ecs describe-services --cluster ai-employee --services ai-employee-service

# Check task definition
aws ecs describe-task-definition --task-definition ai-employee

# Check logs
aws logs tail /ecs/ai-employee --follow
```

#### Database Connection Issues
```bash
# Check security group rules
aws ec2 describe-security-groups --group-ids $DB_SG_ID

# Check subnet group
aws rds describe-db-subnet-groups --db-subnet-group-name ai-employee-subnet-group

# Test connection from container
aws ecs execute-command \
    --cluster ai-employee \
    --task TASK_ID \
    --container ai-employee \
    --command "/bin/sh" \
    --interactive
```

#### Load Balancer Health Checks
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn $TG_ARN

# Check listener rules
aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN
```

## Support

For AWS deployment issues:
- AWS Documentation: https://docs.aws.amazon.com/
- AWS Support Center: https://aws.amazon.com/support/
- Community Forums: https://forums.aws.amazon.com/

## Cleanup

To delete all resources:
```bash
# Delete ECS service
aws ecs delete-service --cluster ai-employee --service ai-employee-service --force

# Delete RDS instance
aws rds delete-db-instance --db-instance-identifier ai-employee-db --skip-final-snapshot

# Delete load balancer
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# Delete VPC
aws ec2 delete-vpc --vpc-id $VPC_ID
```